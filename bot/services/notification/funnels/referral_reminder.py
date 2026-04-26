"""
Воронка напоминания о реферальной программе.

Пользовательская воронка (не ключевая): segment_keys = [] всегда.
Отправляет пользователям, не создавшим реферальную ссылку.
"""

from datetime import timedelta

import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.notification.models import NotificationContext, NotificationResult
from services.notification.rate_limiter import RateLimiter
from services.notification.utils.cache_helpers import NotificationDedupeCache

_DEDUPE_TTL = timedelta(days=7)

_CHECK_SQL = "SELECT EXISTS(SELECT 1 FROM referral_links WHERE referrer_tg_id = $1)"


class ReferralReminderFunnel:
    """Воронка: напоминание о реферальной программе пользователям без реф. ссылки."""

    funnel_id = "referral_reminder"

    def __init__(self, pool: asyncpg.Pool, rate_limiter: RateLimiter) -> None:
        self._pool = pool
        self._rate_limiter = rate_limiter
        self._dedupe = NotificationDedupeCache(pool)

    async def should_send(self, ctx: NotificationContext) -> bool:
        if await self._dedupe.is_sent(self.funnel_id, ctx.user.tg_id):
            return False
        # Проверка в БД: нет реферальной ссылки → не приглашал никого
        async with self._pool.acquire() as conn:
            has_link: bool = await conn.fetchval(_CHECK_SQL, ctx.user.tg_id)
        return not has_link

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        result = NotificationResult(tg_id=ctx.user.tg_id, funnel_id=self.funnel_id)

        send_result = await self._rate_limiter.send_message_safe(
            bot, ctx.user, self._build_text(), self._build_keyboard()
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
            "🤝 <b>Приглашайте друзей — зарабатывайте вместе!</b>\n\n"
            "У вас есть реферальная программа, которую вы ещё не попробовали 😊\n\n"
            "Вот как это работает:\n\n"
            "🔗 <b>Поделитесь своей уникальной ссылкой</b> с другом\n"
            "💰 <b>Получите 10% от его первого платежа</b> — автоматически на баланс\n"
            "🎁 <b>Друг получит бонус</b> при регистрации по вашей ссылке\n\n"
            "Никаких сложностей — просто скопируйте ссылку и отправьте другу. "
            "Всё остальное бот сделает сам! 👇"
        )

    @staticmethod
    def _build_keyboard() -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.button(text="🤝 Реферальная программа", callback_data="open_referral")
        kb.button(text="👤 Личный кабинет", callback_data="profile")
        kb.adjust(1)
        return kb.as_markup()
