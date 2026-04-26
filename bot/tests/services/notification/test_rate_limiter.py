"""
Тесты для RateLimiter.send_message_safe().

Мокируем bot.send_message через AsyncMock.
Исключения aiogram требуют передачи объекта method в конструктор — используем MagicMock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramAPIError,
)

from models import User
from services.notification.rate_limiter import RateLimiter


def make_user(tg_id: int = 123456) -> User:
    return User(
        tg_id=tg_id,
        created_at=datetime.now() - timedelta(days=7),
    )


def make_forbidden_error() -> TelegramForbiddenError:
    method = MagicMock()
    return TelegramForbiddenError(
        method=method, message="Forbidden: bot was blocked by the user"
    )


def make_retry_after_error(seconds: int = 1) -> TelegramRetryAfter:
    method = MagicMock()
    return TelegramRetryAfter(
        method=method, message="Too Many Requests", retry_after=seconds
    )


def make_api_error() -> TelegramAPIError:
    method = MagicMock()
    return TelegramAPIError(method=method, message="Bad Request")


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """RateLimiter с нулевой задержкой для быстрых тестов."""
    return RateLimiter(global_rate=1000, per_user_delay=0.0)


@pytest.fixture
def mock_bot() -> Bot:
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def user() -> User:
    return make_user()


class TestRateLimiterSendMessageSafe:
    """Тесты для send_message_safe()."""

    async def test_successful_send_returns_sent(self, rate_limiter, mock_bot, user):
        mock_bot.send_message.return_value = MagicMock()
        result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "sent"
        mock_bot.send_message.assert_called_once()

    async def test_passes_text_and_keyboard_to_send_message(
        self, rate_limiter, mock_bot, user
    ):
        from aiogram.types import InlineKeyboardMarkup

        keyboard = MagicMock(spec=InlineKeyboardMarkup)
        mock_bot.send_message.return_value = MagicMock()
        await rate_limiter.send_message_safe(mock_bot, user, "Test text", keyboard)
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["text"] == "Test text"
        assert call_kwargs["reply_markup"] is keyboard
        assert call_kwargs["chat_id"] == user.tg_id

    async def test_forbidden_error_returns_blocked(self, rate_limiter, mock_bot, user):
        mock_bot.send_message.side_effect = make_forbidden_error()
        result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "blocked"

    async def test_retry_after_then_success_returns_sent(
        self, rate_limiter, mock_bot, user
    ):
        """Первый вызов бросает RetryAfter, второй — успешен."""
        mock_bot.send_message.side_effect = [
            make_retry_after_error(0),  # retry_after=0 для быстрого теста
            MagicMock(),
        ]
        with patch(
            "services.notification.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "sent"
        assert mock_bot.send_message.call_count == 2

    async def test_retry_after_twice_returns_retry_after(
        self, rate_limiter, mock_bot, user
    ):
        """Оба вызова бросают RetryAfter → возвращает retry_after."""
        mock_bot.send_message.side_effect = [
            make_retry_after_error(0),
            make_retry_after_error(0),
        ]
        with patch(
            "services.notification.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "retry_after"

    async def test_api_error_returns_error(self, rate_limiter, mock_bot, user):
        mock_bot.send_message.side_effect = make_api_error()
        result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "error"

    async def test_retry_after_then_forbidden_returns_blocked(
        self, rate_limiter, mock_bot, user
    ):
        """Первый вызов — RetryAfter, второй — Forbidden → blocked."""
        mock_bot.send_message.side_effect = [
            make_retry_after_error(0),
            make_forbidden_error(),
        ]
        with patch(
            "services.notification.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "blocked"

    async def test_retry_after_then_api_error_returns_error(
        self, rate_limiter, mock_bot, user
    ):
        """Первый вызов — RetryAfter, второй — другая ошибка API → error."""
        mock_bot.send_message.side_effect = [
            make_retry_after_error(0),
            make_api_error(),
        ]
        with patch(
            "services.notification.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await rate_limiter.send_message_safe(mock_bot, user, "Hello")
        assert result == "error"

    async def test_parse_mode_is_html(self, rate_limiter, mock_bot, user):
        """Всегда отправляется с parse_mode=HTML."""
        mock_bot.send_message.return_value = MagicMock()
        await rate_limiter.send_message_safe(mock_bot, user, "text")
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs.get("parse_mode") == "HTML"
