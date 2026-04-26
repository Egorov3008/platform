"""
FunnelManager — оркестратор воронок уведомлений.

Алгоритм работы run_cycle():
  1. Проверить временно́е окно (routing.SENDING_HOUR_WINDOW) по Москве (UTC+3).
  2. Загрузить всех пользователей и ключи из кеша.
  3. Сгруппировать ключи по tg_id.
  4. Для каждого пользователя × воронка:
       - Если воронка ключевая (есть в KEY_SEGMENT_TO_FUNNEL) — отфильтровать ключи
         в нужный сегмент; иначе segment_keys = [].
       - Создать NotificationContext и передать воронке.
"""

import time
from datetime import datetime, timezone, timedelta

import asyncpg
from aiogram import Bot

from logger import logger
from models import Key, User
from services.cache.service import CacheService
from services.core.keys.segmentation import KeySegmentationService
from services.core.segmentation.key_model import KeySegment
from services.notification.models import NotificationContext, FunnelRunReport
from services.notification.protocols import NotificationFunnelProtocol
from services.notification.rate_limiter import RateLimiter
from services.metrics.registry import (
    notification_sent_total,
    notification_blocked_total,
    notification_error_total,
    notification_cycle_duration,
)
from services.notification.routing import KEY_SEGMENT_TO_FUNNEL, SENDING_HOUR_WINDOW

# Московское время (UTC+3)
_MOSCOW_TZ = timezone(timedelta(hours=3))

# Обратный маппинг: funnel_id → KeySegment (только для ключевых воронок)
_SEGMENT_BY_FUNNEL: dict[str, KeySegment] = {
    v: k for k, v in KEY_SEGMENT_TO_FUNNEL.items()
}


class FunnelManager:
    """Оркестратор воронок уведомлений."""

    def __init__(self, cache: CacheService, pool: asyncpg.Pool) -> None:
        self._cache = cache
        self._pool = pool
        self._funnels: list[NotificationFunnelProtocol] = []
        self._rate_limiter = RateLimiter()
        self._seg_service: KeySegmentationService | None = None  # Создаётся в run_cycle()

    def register(self, funnel: NotificationFunnelProtocol) -> None:
        """Зарегистрировать воронку."""
        self._funnels.append(funnel)
        logger.debug("Зарегистрирована воронка", funnel_id=funnel.funnel_id)

    async def run_cycle(self, bot: Bot) -> FunnelRunReport:
        """Запустить один цикл уведомлений по всем воронкам."""
        report = FunnelRunReport()
        t0 = time.monotonic()

        if not self._in_sending_window():
            logger.info("Уведомления: нерабочее время, пропуск цикла")
            return report

        # ⚠️ КРИТИЧНО: Создаём новый KeySegmentationService для КАЖДОГО цикла
        # чтобы гарантировать, что TimeHelper использует актуальное время
        # (не кэшированное из предыдущего цикла)
        self._seg_service = KeySegmentationService()

        users: list[User] = await self._cache.users.all()
        all_keys: list[Key] = await self._cache.keys.all()

        keys_by_user: dict[int, list[Key]] = {}
        for key in all_keys:
            keys_by_user.setdefault(key.tg_id, []).append(key)

        report.total_users = len(users)
        logger.info(
            "Запуск цикла уведомлений",
            users=len(users),
            funnels=len(self._funnels),
        )

        for user in users:
            if user.is_blocked:
                continue

            user_keys = keys_by_user.get(user.tg_id, [])

            for funnel in self._funnels:
                try:
                    segment_keys = await self._get_segment_keys(
                        funnel.funnel_id, user_keys
                    )
                    ctx = NotificationContext(
                        user=user,
                        keys=user_keys,
                        segment_keys=segment_keys,
                    )

                    if not await funnel.should_send(ctx):
                        continue

                    result = await funnel.process(bot, ctx)
                    report.add_result(result)
                    report.total_keys_segmented += len(segment_keys)

                except Exception as exc:
                    logger.error(
                        "Ошибка в воронке",
                        funnel_id=funnel.funnel_id,
                        tg_id=user.tg_id,
                        error=str(exc),
                    )

        report.duration_seconds = time.monotonic() - t0

        # Prometheus: экспорт метрик из FunnelRunReport
        for funnel_id, stats in report.results_by_funnel.items():
            notification_sent_total.labels(funnel_id=funnel_id).inc(stats.get("sent", 0))
            notification_blocked_total.labels(funnel_id=funnel_id).inc(
                stats.get("failed_blocked", 0)
            )
            notification_error_total.labels(funnel_id=funnel_id).inc(
                stats.get("failed_other", 0)
            )
        notification_cycle_duration.observe(report.duration_seconds)

        logger.info(
            "Цикл уведомлений завершён",
            users=report.total_users,
            keys_segmented=report.total_keys_segmented,
            duration=f"{report.duration_seconds:.1f}s",
            results=report.results_by_funnel,
        )
        return report

    async def _get_segment_keys(
        self, funnel_id: str, user_keys: list[Key]
    ) -> list[Key]:
        """Получить ключи для воронки (для ключевых воронок — по сегменту; иначе [])."""
        segment = _SEGMENT_BY_FUNNEL.get(funnel_id)
        if segment is None or not user_keys or self._seg_service is None:
            return []
        try:
            filtered = await self._seg_service.segmenter.filter_keys(user_keys, segment)
            return filtered
        except Exception as e:
            logger.error(
                "Ошибка при фильтрации ключей",
                funnel_id=funnel_id,
                segment=segment.name if segment else None,
                error=str(e),
                exc_info=True,
            )
            return []

    @staticmethod
    def _in_sending_window() -> bool:
        start, end = SENDING_HOUR_WINDOW
        moscow_now = datetime.now(_MOSCOW_TZ)
        return start <= moscow_now.hour < end
