from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update

from client import XUISession
from logger import logger


class XUIMiddleware(BaseMiddleware):
    """
    Получает xui_session через DI-контейнер.
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if not (user := data.get("event_from_user")):
            return await handler(event, data)

        container = data["container"]
        xui_session = container.resolve(XUISession)

        data["xui_session"] = xui_session
        logger.debug("XUI сессия добавлена в контекст", user_id=user.id)

        try:
            return await handler(event, data)
        finally:
            pass
