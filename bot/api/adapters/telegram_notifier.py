"""Адаптер уведомлений для Telegram Bot API.

Реализует протокол NotificationSender через aiogram Bot.
Это позволяет бизнес-логике не зависеть от Telegram напрямую.
"""

from __future__ import annotations

from typing import Any, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SUPPORT_CHAT_URL
from logger import logger
from services.core.protocols import MessageBuilder, NotificationSender


class TelegramNotificationSender(NotificationSender):
    """Реализация NotificationSender через Telegram Bot API.

    Внедряется через DI контейнер, что позволяет заменять реализацию
    для тестов (mock) или других каналов (email, SMS).
    """

    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Any] = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: Optional[bool] = None,
    ) -> None:
        """Отправить сообщение через Telegram."""
        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except TelegramAPIError as e:
            logger.warning(
                "Не удалось отправить уведомление через Telegram",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def send_photo(
        self,
        chat_id: int,
        photo: Any,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        parse_mode: str = "HTML",
    ) -> None:
        """Отправить фото через Telegram."""
        try:
            await self._bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except TelegramAPIError as e:
            logger.warning(
                "Не удалось отправить фото через Telegram",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class TelegramMessageBuilder(MessageBuilder):
    """Реализация MessageBuilder для Telegram inline-клавиатур."""

    def build_support_keyboard(
        self,
        support_url: str = SUPPORT_CHAT_URL,
        profile_callback: str = "profile",
    ) -> InlineKeyboardMarkup:
        """Построить клавиатуру с кнопками поддержки и профиля."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardBuilder().button(text="Техническая поддержка", url=support_url).export(),
            InlineKeyboardBuilder().button(text="Личный кабинет", callback_data=profile_callback).export(),
        )
        return builder.as_markup()

    def build_renewal_keyboard(
        self,
        support_url: str = "https://t.me/support_chat",
    ) -> InlineKeyboardMarkup:
        """Построить клавиатуру для сообщения о продлении."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardBuilder().button(text="Техническая поддержка", url=support_url).export(),
        )
        return builder.as_markup()
