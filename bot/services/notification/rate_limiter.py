"""
RateLimiter — контроль частоты отправки сообщений через Telegram Bot API.

Реализует token-bucket алгоритм:
- 25 сообщений/сек глобально
- Минимум 1.1 сек между сообщениями одному пользователю
"""

import asyncio
import time
from typing import Literal, Optional

import asyncpg
from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramAPIError,
    TelegramBadRequest,
)
from aiogram.types import InlineKeyboardMarkup

from logger import logger
from models import User
from services.metrics.registry import (
    telegram_messages_sent_total,
    telegram_flood_control_total,
    rate_limiter_tokens,
)

SendResult = Literal["sent", "blocked", "retry_after", "error"]

# Глобальные параметры rate limiter
_GLOBAL_RATE = 25  # сообщений в секунду
_PER_USER_DELAY = 1.1  # секунд между сообщениями одному пользователю


class RateLimiter:
    """
    Singleton-совместимый rate limiter для отправки Telegram-сообщений.

    Управляет:
    - Глобальным token bucket (25 msg/sec)
    - Задержкой per-user (1.1 сек)
    """

    def __init__(
        self,
        global_rate: float = _GLOBAL_RATE,
        per_user_delay: float = _PER_USER_DELAY,
        pool: Optional[asyncpg.Pool] = None,
    ):
        self._global_rate = global_rate
        self._per_user_delay = per_user_delay
        self._tokens: float = global_rate
        self._last_refill: float = time.monotonic()
        self._last_sent: dict[int, float] = {}
        self._lock = asyncio.Lock()
        self._pool = pool

    async def _acquire(self, tg_id: int) -> None:
        """Дождаться, пока можно безопасно отправить сообщение."""
        async with self._lock:
            now = time.monotonic()

            # Пополнение токенов
            elapsed = now - self._last_refill
            self._tokens = min(
                self._global_rate,
                self._tokens + elapsed * self._global_rate,
            )
            self._last_refill = now

            # Ожидание per-user
            last = self._last_sent.get(tg_id, 0.0)
            wait_user = max(0.0, self._per_user_delay - (now - last))

            # Ожидание глобального токена
            wait_global = (
                0.0 if self._tokens >= 1 else (1 - self._tokens) / self._global_rate
            )

            wait = max(wait_user, wait_global)
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self._global_rate,
                    self._tokens + elapsed * self._global_rate,
                )
                self._last_refill = now

            self._tokens -= 1
            self._last_sent[tg_id] = time.monotonic()
            rate_limiter_tokens.set(self._tokens)

    async def _mark_user_blocked(self, tg_id: int) -> None:
        """Пометить пользователя как заблокированного в БД."""
        if not self._pool:
            logger.warning(
                "Не удалось пометить пользователя как заблокированного: pool не инициализирован",
                tg_id=tg_id,
            )
            return

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_blocked = TRUE, updated_at = NOW() WHERE tg_id = $1",
                    tg_id,
                )
            logger.info("Пользователь помечен как заблокированный", tg_id=tg_id)
        except Exception as e:
            logger.error(
                "Ошибка при пометке пользователя как заблокированного",
                tg_id=tg_id,
                error=str(e),
            )

    async def send_message_safe(
        self,
        bot: Bot,
        user: User,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
    ) -> SendResult:
        """
        Безопасная отправка сообщения с учётом rate limiting.

        При TelegramRetryAfter — один retry после sleep.
        При TelegramForbiddenError или "chat not found" — помечает пользователя как заблокированного.

        Returns:
            "sent"        — успешно отправлено
            "blocked"     — пользователь заблокировал бота
            "retry_after" — retry_after случился дважды (пропускаем)
            "error"       — другая ошибка Telegram API
        """
        tg_id = user.tg_id
        await self._acquire(tg_id)

        try:
            await bot.send_message(
                chat_id=tg_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            telegram_messages_sent_total.labels(result="sent").inc()
            return "sent"

        except TelegramForbiddenError:
            logger.info("Пользователь заблокировал бота", tg_id=tg_id)
            await self._mark_user_blocked(tg_id)
            telegram_messages_sent_total.labels(result="blocked").inc()
            return "blocked"

        except TelegramBadRequest as e:
            # Обработка ошибок "chat not found" и других Bad Request
            error_msg = str(e)
            if "chat not found" in error_msg or "CHAT_NOT_FOUND" in error_msg:
                logger.info(
                    "Чат не найден (пользователь удалил диалог или заблокировал бота)",
                    tg_id=tg_id,
                )
                await self._mark_user_blocked(tg_id)
                telegram_messages_sent_total.labels(result="blocked").inc()
                return "blocked"
            else:
                logger.error("Ошибка Telegram API", tg_id=tg_id, error=error_msg)
                telegram_messages_sent_total.labels(result="error").inc()
                return "error"

        except TelegramRetryAfter as exc:
            logger.warning(
                "Flood control, retry after", seconds=exc.retry_after, tg_id=tg_id
            )
            telegram_flood_control_total.inc()
            await asyncio.sleep(exc.retry_after)
            try:
                await self._acquire(tg_id)
                await bot.send_message(
                    chat_id=tg_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                telegram_messages_sent_total.labels(result="sent").inc()
                return "sent"
            except TelegramRetryAfter:
                logger.warning("Повторный flood control, пропускаем", tg_id=tg_id)
                telegram_messages_sent_total.labels(result="retry_after").inc()
                return "retry_after"
            except TelegramForbiddenError:
                await self._mark_user_blocked(tg_id)
                telegram_messages_sent_total.labels(result="blocked").inc()
                return "blocked"
            except TelegramBadRequest as e:
                error_msg = str(e)
                if "chat not found" in error_msg or "CHAT_NOT_FOUND" in error_msg:
                    await self._mark_user_blocked(tg_id)
                    telegram_messages_sent_total.labels(result="blocked").inc()
                    return "blocked"
                else:
                    logger.error(
                        "Ошибка Telegram API при повторе", tg_id=tg_id, error=error_msg
                    )
                    telegram_messages_sent_total.labels(result="error").inc()
                    return "error"
            except TelegramAPIError as e:
                logger.error(
                    "Ошибка Telegram API при повторе", tg_id=tg_id, error=str(e)
                )
                telegram_messages_sent_total.labels(result="error").inc()
                return "error"

        except TelegramAPIError as exc:
            logger.error("Ошибка Telegram API", tg_id=tg_id, error=str(exc))
            telegram_messages_sent_total.labels(result="error").inc()
            return "error"
