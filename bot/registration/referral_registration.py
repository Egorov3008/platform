from typing import Dict, Any, Optional

from logger import logger
from api.backend_client import BackendAPIClient
from .base_registration import BaseRegistration


class ReferralRegistration(BaseRegistration):
    """Обработка регистрации по реферальной ссылке."""

    def __init__(self, backend: BackendAPIClient):
        super().__init__()
        self._backend = backend

    async def can_handle(self, token: str) -> bool:
        """Проверяет, является ли токен реферальной ссылкой."""
        link = await self._backend.get_referral_link_by_token(token)
        return link is not None

    async def register(self, token: str) -> Dict[str, Any]:
        """Возвращает данные для регистрации по реферальной ссылке."""
        link = await self._backend.get_referral_link_by_token(token)
        if not link:
            logger.warning("Реферальная ссылка не найдена", token=token)
            return {"success": False, "error": "referral_link_not_found"}

        return {
            "success": True,
            "type": "referral",
            "token": token,
            "referrer_tg_id": link.get("referrer_tg_id"),
            "referral_link_id": link.get("id"),
        }
