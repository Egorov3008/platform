from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update

from logger import logger
from registration.gift_registration import GiftRegistration
from registration.referral_registration import ReferralRegistration
from registration.registration_factory import RegistrationFactory
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

        if not (user := data.get("event_from_user")):
            return await handler(event, data)

        user_id = user.id

        # Проверяем backend API (single source of truth).
        # get_user() возвращает None, если пользователь не зарегистрирован — это
        # нормальная ситуация, а не ошибка: идём дальше по flow регистрации.
        try:
            from api.backend_client import BackendAPIClient

            backend_client = container.resolve(BackendAPIClient)
            backend_user = await backend_client.get_user(user_id)
            if backend_user:
                # backend_user может быть dict, dataclass или pydantic DTO — извлекаем trial безопасным способом.
                if isinstance(backend_user, dict):
                    trial = backend_user.get("trial", 0)
                else:
                    trial = getattr(backend_user, "trial", 0)
                data["registration_result"] = {
                    "success": True,
                    "type": "registered_user",
                    "trial": trial,
                }
                return await handler(event, data)
        except Exception as e:
            logger.warning(
                "Ошибка при проверке пользователя в backend", user_id=user_id, error=str(e)
            )

        # Пользователь не найден в backend. Если есть токен /start xxx —
        # пытаемся зарегистрировать его (gift / referral). Если токена нет —
        # помечаем как unknown_user, чтобы handler /start вызвал auto_register_user.
        if not self.check_event_message(event):
            data.setdefault(
                "registration_result",
                {"success": False, "type": "unknown_user"},
            )
            return await handler(event, data)

        token = await self.get_start_message(event)
        if not token:
            data["registration_result"] = {
                "success": False,
                "type": "unknown_user",
            }
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
        else:
            # Токен был, но регистрация не удалась — пусть handler решает.
            data.setdefault(
                "registration_result",
                {"success": False, "type": "unknown_user"},
            )

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
