"""
Воронка реферальных уведомлений.

Пользовательская воронка (не ключевая): segment_keys = [] всегда.
Отправляет приветственное сообщение пользователям, пришедшим по реферальной ссылке.
"""

from datetime import timedelta

import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.notification.models import NotificationContext, NotificationResult
from services.notification.rate_limiter import RateLimiter
from services.notification.utils.cache_helpers import NotificationDedupeCache

_DEDUPE_TTL = timedelta(days=3)


class ReferralBonusFunnel:
    """Воронка: приветственное сообщение реферальным пользователям."""

    funnel_id = "referral_bonus"

    def __init__(self, pool: asyncpg.Pool, rate_limiter: RateLimiter) -> None:
        self._rate_limiter = rate_limiter
        self._dedupe = NotificationDedupeCache(pool)

    async def should_send(self, ctx: NotificationContext) -> bool:
        # Только пользователи с реферальной ссылкой, не активировавшие trial
        if ctx.user.referral_id is None:
            return False
        if ctx.user.trial != 0:
            return False
        return not await self._dedupe.is_sent(self.funnel_id, ctx.user.tg_id)

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        result = NotificationResult(tg_id=ctx.user.tg_id, funnel_id=self.funnel_id)

        text = self._build_text()
        keyboard = self._build_keyboard()

        send_result = await self._rate_limiter.send_message_safe(
            bot, ctx.user, text, keyboard
        )

        if send_result == "sent":
            result.sent += 1
            await self._dedupe.mark_sent(self.funnel_id, ctx.user.tg_id, _DEDUPE_TTL)
        elif send_result == "blocked":
            result.failed_blocked += 1
        else:
            result.failed_other += 1

        return result

    @staticmethod
    def _build_text() -> str:
        return (
            "🎉 <b>Вас пригласил друг!</b>\n\n"
            "Активируйте пробный период и получите:\n\n"
            "🆓 <b>7 дней бесплатного пользования</b>\n"
            "📦 <b>10 ГБ трафика</b>\n"
            "⚡️ <b>Полный доступ ко всем функциям</b>\n\n"
            "Начните прямо сейчас! 👇"
        )

    @staticmethod
    def _build_keyboard() -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.button(text="🎁 Активировать пробный период", callback_data="activate_stock")
        kb.button(text="👤 Личный кабинет", callback_data="profile")
        kb.adjust(1)
        return kb.as_markup()
