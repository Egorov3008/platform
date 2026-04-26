from collections.abc import Awaitable, Callable
from typing import Any

import asyncpg
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DatabaseMiddleware(BaseMiddleware):
    """
    Внедряет asyncpg.Connection в data из пула подключений.

    Используется пул из DI контейнера, который более эффективен,
    чем создание нового подключения на каждое событие.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        container = data.get("container")
        if not container:
            # Fallback, если контейнер не был инициализирован
            return await handler(event, data)

        pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
        async with pool.acquire() as conn:
            data["session"] = conn
            return await handler(event, data)
