from typing import Dict, Any

from .base_registration import BaseRegistration


class LandingRegistration(BaseRegistration):
    """Обработчик регистрации по лендинг-ссылке /start landing_<uid>.

    Чистая проверка префикса — без обращения к бэкенду. Регистрируется в
    RegistrationFactory ПЕРВЫМ, чтобы landing-токены short-circuit'ились до
    gift/referral (которые делают сетевые запросы в can_handle).

    Сама регистрация юзера и привязка ключа выполняется в
    bot/handlers/start_from_landing.py — здесь только распознавание токена.
    """

    PREFIX = "landing_"

    async def can_handle(self, token: str) -> bool:
        return bool(token) and token.startswith(self.PREFIX)

    async def register(self, token: str) -> Dict[str, Any]:
        landing_uid = token.removeprefix(self.PREFIX)
        return {
            "success": True,
            "type": "landing",
            "landing_uid": landing_uid,
            "is_registered": False,
        }