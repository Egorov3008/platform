import asyncio
import time
from typing import Optional, Any

import asyncpg
from aiohttp import web
from aiogram import Bot
from payments.pyments_webhook import app as webhook_app, init_webhook_service
from config import WEBHOOK_HOST, WEBHOOK_PORT

from logger import logger
from services.metrics.registry import (
    background_sync_last_run,
    background_sync_duration,
    background_sync_errors_total,
    background_notification_last_run,
)


class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        self.running = False
        self._cache_synced = asyncio.Event()
        self._last_sync_time: Optional[float] = None
        self._last_sync_duration: Optional[float] = None
        self._sync_error_count: int = 0
        self._last_notification_time: Optional[float] = None
        self._last_notification_report: Optional[Any] = None  # FunnelRunReport
        self.notifications_enabled: bool = False  # Флаг управления уведомлениями (по умолчанию выключено)

    def enable_notifications(self) -> None:
        """Включить отправку уведомлений."""
        self.notifications_enabled = True
        logger.info("Уведомления включены")

    def disable_notifications(self) -> None:
        """Выключить отправку уведомлений."""
        self.notifications_enabled = False
        logger.info("Уведомления выключены")

    def is_notifications_enabled(self) -> bool:
        """Проверить, включены ли уведомления."""
        return self.notifications_enabled

    async def start_sync_cache(self, container) -> None:
        """Синхронизация панели XUI с кешем и БД каждые 3 часа."""
        from services.synchron.database_synchronizer import DatabaseSynchronizer
        from services.synchron.xui_fetcher import XUIFetcher
        from services.synchron.cache_comparator import CacheComparator
        from services.synchron.key_creator import KeyCreator
        from services.synchron.traffic import TrafficUpdater
        from services.synchron.tariff_matcher import TariffMatcher
        from services.core.data.service import ServiceDataModel
        from client import XUISession

        model_data: ServiceDataModel = container.resolve(ServiceDataModel)
        pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
        xui_session: XUISession = container.resolve(XUISession)

        synchronizer = DatabaseSynchronizer(
            xui_fetcher=XUIFetcher(),
            cache_comparator=CacheComparator(),
            key_creator=KeyCreator(model_data, pool, TariffMatcher(model_data)),
            traffic_updater=TrafficUpdater(model_data),
            model_data=model_data,
            pool=pool,
        )

        while self.running:
            try:
                logger.info("Запуск синхронизации кэша с XUI панелью")
                t0 = time.monotonic()
                result = await synchronizer.sync_data(xui_session)
                elapsed = time.monotonic() - t0
                background_sync_duration.observe(elapsed)
                background_sync_last_run.set_to_current_time()
                self._last_sync_time = time.time()
                self._last_sync_duration = elapsed
                logger.info("Синхронизация завершена", result=result)
                self._cache_synced.set()
                await asyncio.sleep(3 * 3600)  # каждые 3 часа
            except Exception as e:
                background_sync_errors_total.inc()
                self._sync_error_count += 1
                logger.error(
                    "Критическая ошибка синхронизации",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                await asyncio.sleep(300)  # 5 минут при ошибке

        await synchronizer.close()

    async def start_notification_bot(self, container, bot: Bot) -> None:
        """Запуск цикла уведомлений каждый час. Ждёт первую синхронизацию кеша."""
        from services.cache.service import CacheService
        from services.notification.manager import FunnelManager
        from services.notification.rate_limiter import RateLimiter
        from services.notification.funnels.key_expiry_24h import KeyExpiryFunnel24h
        from services.notification.funnels.key_expiry_10h import KeyExpiryFunnel10h
        from services.notification.funnels.trial_reminder import TrialReminderFunnel
        from services.notification.funnels.cold_lead_engagement import ColdLeadFunnel
        from services.notification.funnels.referral_bonus import ReferralBonusFunnel
        from services.notification.funnels.referral_reminder import ReferralReminderFunnel

        # Ждём завершения первой синхронизации кеша для точной сегментации
        # Таймаут 10 минут — если синхронизация не завершилась, запускаем без неё
        logger.info("Уведомления ожидают первую синхронизацию кеша...")
        try:
            await asyncio.wait_for(self._cache_synced.wait(), timeout=600)
            logger.info("Кеш синхронизирован, запуск цикла уведомлений")
        except asyncio.TimeoutError:
            logger.warning(
                "Синхронизация кеша не завершилась за 10 минут, "
                "запуск уведомлений без полной синхронизации"
            )

        cache: CacheService = container.resolve(CacheService)
        pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
        rate_limiter = RateLimiter(pool=pool)

        funnel_manager = FunnelManager(cache=cache, pool=pool)
        funnel_manager.register(
            KeyExpiryFunnel24h(cache=cache, pool=pool, rate_limiter=rate_limiter)
        )
        funnel_manager.register(
            KeyExpiryFunnel10h(cache=cache, pool=pool, rate_limiter=rate_limiter)
        )
        funnel_manager.register(
            TrialReminderFunnel(pool=pool, rate_limiter=rate_limiter)
        )
        funnel_manager.register(ColdLeadFunnel(pool=pool, rate_limiter=rate_limiter))
        funnel_manager.register(
            ReferralBonusFunnel(pool=pool, rate_limiter=rate_limiter)
        )
        funnel_manager.register(
            ReferralReminderFunnel(pool=pool, rate_limiter=rate_limiter)
        )

        while self.running:
            try:
                # Проверяем флаг уведомлений перед каждым циклом
                if not self.notifications_enabled:
                    logger.debug("Уведомления отключены, пропуск цикла")
                    await asyncio.sleep(3600)  # каждый час проверяем снова
                    continue

                report = await funnel_manager.run_cycle(bot)
                background_notification_last_run.set_to_current_time()
                self._last_notification_time = time.time()
                self._last_notification_report = report
                logger.debug(
                    "Цикл уведомлений завершён", duration=report.duration_seconds
                )
                await asyncio.sleep(3600)  # каждый час
            except Exception as e:
                logger.error("Ошибка в цикле уведомлений", error=str(e))
                await asyncio.sleep(60)  # 1 минута при ошибке

    async def run_webhook_server(self) -> None:
        """Запуск вебхук сервера."""
        try:
            await init_webhook_service()
            runner = web.AppRunner(webhook_app)
            await runner.setup()
            port = int(WEBHOOK_PORT) if WEBHOOK_PORT is not None else 8080
            site = web.TCPSite(runner, host=WEBHOOK_HOST, port=port)
            await site.start()
            logger.success("Webhook server started", WEBHOOK_PORT=WEBHOOK_PORT)
        except Exception as e:
            logger.error(
                "Failed to start webhook server",
                error_type=type(e).__name__,
                error_message=str(e)
            )

    def get_status(self) -> dict:
        """Возвращает текущий статус фоновых задач."""
        return {
            "sync": {
                "last_run": self._last_sync_time,
                "duration": self._last_sync_duration,
                "error_count": self._sync_error_count,
            },
            "notifications": {
                "enabled": self.notifications_enabled,
                "last_run": self._last_notification_time,
                "report": self._last_notification_report,
            },
            "tasks_alive": {
                name: not task.done()
                for name, task in self.tasks.items()
            },
        }

    async def start_all_tasks(self, container, bot: Bot) -> None:
        """Запуск всех фоновых задач."""
        self.running = True
        self.tasks["sync_cache"] = asyncio.create_task(
            self.start_sync_cache(container),
            name="sync_cache",
        )
        self.tasks["notification_bot"] = asyncio.create_task(
            self.start_notification_bot(container, bot),
            name="notification_bot",
        )
        self.tasks["webhook"] = asyncio.create_task(
            self.run_webhook_server(),
            name="webhook_server",
        )
        logger.info("Все фоновые задачи запущены")

    async def stop_all_tasks(self) -> None:
        """Остановка всех фоновых задач."""
        self.running = False
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                logger.info("Остановка задачи", task_name=name)

        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        logger.info("Все фоновые задачи остановлены")


# Глобальный менеджер
task_manager = BackgroundTaskManager()
