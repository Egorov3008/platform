"""
Воронка уведомлений об истечении ключей (за 24 часа до окончания).

Сегмент: KeySegment.EXPIRING_24H → funnel_id = "key_expiry_24h".
Менеджер передаёт в ctx.segment_keys уже отфильтрованные ключи.
"""

from datetime import datetime, timedelta

import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from logger import logger
from models import Key
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.notification.models import NotificationContext, NotificationResult
from services.notification.rate_limiter import RateLimiter
from services.notification.utils.cache_helpers import NotificationDedupeCache

_DEDUPE_TTL = timedelta(hours=25)
_cache_keys = CacheKeyManager()


class KeyExpiryFunnel24h:
    """Воронка: уведомление об истечении ключа за 24 часа."""

    funnel_id = "key_expiry_24h"

    def __init__(
        self,
        cache: CacheService,
        pool: asyncpg.Pool,
        rate_limiter: RateLimiter,
    ) -> None:
        self._cache = cache
        self._pool = pool
        self._rate_limiter = rate_limiter
        self._dedupe = NotificationDedupeCache(pool)

    async def should_send(self, ctx: NotificationContext) -> bool:
        """Отправлять, если есть ключи в сегменте."""
        return bool(ctx.segment_keys)

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        """Отправить уведомление для каждого истекающего ключа."""
        result = NotificationResult(tg_id=ctx.user.tg_id, funnel_id=self.funnel_id)

        for key in ctx.segment_keys:
            # Пропускаем, если уже уведомлён (по флагу на ключе)
            if key.notified_24h:
                result.skipped += 1
                continue

            # Пропускаем, если уже отправляли в этом цикле (дедупликация)
            dedupe_id = f"{self.funnel_id}:{key.email}"
            if await self._dedupe.is_sent(dedupe_id, ctx.user.tg_id):
                result.skipped += 1
                continue

            text = self._build_text(key)
            keyboard = self._build_keyboard(key)

            send_result = await self._rate_limiter.send_message_safe(
                bot, ctx.user, text, keyboard
            )

            if send_result == "sent":
                result.sent += 1
                await self._dedupe.mark_sent(dedupe_id, ctx.user.tg_id, _DEDUPE_TTL)
                await self._mark_notified(key)
            elif send_result == "blocked":
                result.failed_blocked += 1
            else:
                result.failed_other += 1

        return result

    def _build_text(self, key: Key) -> str:
        expiry_dt = datetime.fromtimestamp(key.expiry_time / 1000)
        hours_left = max(0, int((expiry_dt - datetime.now()).total_seconds() // 3600))
        return (
            f"⚠️ <b>Ваш ключ истекает через {hours_left} ч.</b>\n"
            f"📧 {key.email}\n"
            f"⏳ {expiry_dt:%d.%m.%Y %H:%M}\n\n"
            "Продлите доступ, чтобы не потерять подключение к VPN."
        )

    @staticmethod
    def _build_keyboard(key: Key) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Продлить ключ", callback_data=f"renew_key|{key.email}")
        kb.button(text="👤 Личный кабинет", callback_data="profile")
        kb.adjust(1)
        return kb.as_markup()

    async def _mark_notified(self, key: Key) -> None:
        """Пометить ключ как уведомлённый в кеше и БД."""
        key.notified_24h = True
        try:
            await self._cache.keys.set(_cache_keys.key(key.email), key)
        except Exception as exc:
            logger.error(
                "Ошибка обновления кеша ключа", email=key.email, error=str(exc)
            )

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE keys SET notified_24h = TRUE WHERE email = $1",
                    key.email,
                )
        except Exception as exc:
            logger.error("Ошибка обновления БД ключа", email=key.email, error=str(exc))
