# middlewares/dependency_injection.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from punq import Container

from services.container.app import get_container


class DependencyInjectionMiddleware(BaseMiddleware):
    """
    Middleware, который добавляет DI-контейнер в `data`.
    Все остальные middleware и хендлеры смогут получать зависимости через него.
    """

    container: Container = None  # Статический контейнер (инициализируется один раз)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Инициализируем контейнер один раз
        if DependencyInjectionMiddleware.container is None:
            DependencyInjectionMiddleware.container = await get_container()

        # Добавляем контейнер в данные
        data["container"] = DependencyInjectionMiddleware.container

        return await handler(event, data)
