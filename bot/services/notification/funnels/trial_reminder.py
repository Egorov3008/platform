"""
Воронка уведомлений о неиспользованном trial-ключе.

Сегмент: KeySegment.TRIAL → funnel_id = "trial_unused".
Цель: пользователи, которые активировали пробный период, но не подключились.
"""

from datetime import timedelta
from typing import List

import asyncpg
from aiogram import Bot
from aiogram.types import CopyTextButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SUPPORT_CHAT_URL
from models.keys.key import Key
from services.notification.models import NotificationContext, NotificationResult
from services.notification.rate_limiter import RateLimiter
from services.notification.utils.cache_helpers import NotificationDedupeCache

_DEDUPE_TTL = timedelta(days=3)


class TrialReminderFunnel:
    """Воронка: напоминание пользователям с неиспользованным trial-ключом."""

    funnel_id = "trial_unused"

    def __init__(self, pool: asyncpg.Pool, rate_limiter: RateLimiter) -> None:
        self._rate_limiter = rate_limiter
        self._dedupe = NotificationDedupeCache(pool)

    async def should_send(self, ctx: NotificationContext) -> bool:
        # segment_keys = trial-ключи (pre-filtered менеджером)
        if not ctx.segment_keys:
            return False

        # Есть ли ключ с нулевым трафиком (пользователь не подключался)?
        unused = [k for k in ctx.segment_keys if (k.used_traffic or 0.0) == 0.0]
        if not unused:
            return False

        return not await self._dedupe.is_sent(self.funnel_id, ctx.user.tg_id)

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        result = NotificationResult(tg_id=ctx.user.tg_id, funnel_id=self.funnel_id)
        key = next((k for k in ctx.segment_keys if (k.used_traffic or 0.0) == 0.0), None)
        if key is None:
            result.failed_other += 1
            return result

        link_to_connect = f"https://tds-pro.space/vless/{key.key}"
        link_key = CopyTextButton(text=key.key)

        text = self._build_text(key.email)
        keyboard = self._build_keyboard(link_to_connect, link_key)

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
    def _build_text(email: str) -> str:
        return (
            f"🎁 <b>Ваш ключ {email} активирован!</b>\n\n"
            "Похоже, вы ещё не подключились к VPN. Давайте попробуем вместе?\n\n"
            "1. Скачайте приложение для нашего VPN:\n"
            "2. Согласитесь со всеми изменениями\n"
            "3. Просто нажмите 'Вставить ключ в приложение'\n"
            "Если не получается, напишите нам, мы поможем\n"
        )

    @staticmethod
    def _build_keyboard(link_to_connect: str, link_key: CopyTextButton) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.button(text="🚀 Вставить ключ в приложение", url=link_to_connect)
        kb.button(text="Скопировать ключ", copy_text=link_key)
        kb.button(text="Техническая поддержка", url=SUPPORT_CHAT_URL)
        kb.button(text="👤 Личный кабинет", callback_data="profile")
        kb.adjust(1)
        return kb.as_markup()

    