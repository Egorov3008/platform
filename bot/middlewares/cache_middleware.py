from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from services.cache.service import CacheService


class CacheMiddleware(BaseMiddleware):
    """
    Автоматически внедряет cache_service в data.
    """

    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["cache"] = self.cache_service
        return await handler(event, data)
