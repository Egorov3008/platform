from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update

from logger import logger
from registration.gift_registration import GiftRegistration
from registration.referral_registration import ReferralRegistration
from registration.registration_factory import RegistrationFactory
from services.cache.key_manager import CacheKeyManager
from services.metrics.registry import user_registered_total


class RegistrationUsersMiddleware(BaseMiddleware):
    """
    Обрабатывает регистрацию пользователей через специальные токены.

    Использует компоненты регистрации из DI контейнера вместо их создания вручную.
    """

    def __init__(self):
        pass  # Ничего не инициализируем — зависимости придёт контейнер

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        container = data["container"]
        cache = data["cache"]

        if not (user := data.get("event_from_user")):
            return await handler(event, data)

        user_id = user.id

        # Проверяем кеш
        cached_user = await cache.users.get(CacheKeyManager.user(user_id))
        if cached_user:
            data["registration_result"] = {"success": True, "type": "registered_user"}
            return await handler(event, data)

        # Fallback: проверяем backend API если кеша нет (кеш мог истечь или быть очищен)
        try:
            from api.backend_client import BackendAPIClient

            backend_client = container.resolve(BackendAPIClient)
            backend_user = await backend_client.get_user(user_id)
            if backend_user:
                logger.debug("Пользователь найден в backend (кеш был пуст)", user_id=user_id)
                data["registration_result"] = {
                    "success": True,
                    "type": "registered_user",
                }
                return await handler(event, data)
        except Exception as e:
            logger.warning(
                "Ошибка при проверке пользователя в backend", user_id=user_id, error=str(e)
            )

        if not self.check_event_message(event):
            return await handler(event, data)

        token = await self.get_start_message(event)
        if not token:
            return await handler(event, data)

        # Резолвим зависимости из контейнера
        factory: RegistrationFactory = container.resolve(RegistrationFactory)
        gift_registration: GiftRegistration = container.resolve(GiftRegistration)
        referral_registration: ReferralRegistration = container.resolve(
            ReferralRegistration
        )

        # Используем синглтоны из контейнера
        factory.register_handler(gift_registration)
        factory.register_handler(referral_registration)
        result = await factory.handle_registration(token)

        if result["success"]:
            logger.info("Регистрация успешна", user_id=user_id, type=result["type"])
            user_registered_total.labels(type=result.get("type", "unknown")).inc()
            data["registration_result"] = result

        return await handler(event, data)

    def check_event_message(self, event: Update) -> bool:
        if not isinstance(event, Update):
            return False
        return bool(event.message or event.edited_message)

    async def get_start_message(self, event: Update) -> str | None:
        message = event.message or event.edited_message
        if message.text and message.text.startswith("/start"):
            parts = message.text.split()
            return parts[1] if len(parts) > 1 else None
        return None
