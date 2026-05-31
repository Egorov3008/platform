from typing import Dict, Any, Optional

from logger import logger
from api.backend_client import BackendAPIClient
from .base_registration import BaseRegistration


class GiftRegistration(BaseRegistration):
    def __init__(self, backend: BackendAPIClient):
        super().__init__()
        self._backend = backend

    async def can_handle(self, token: str) -> bool:
        """Проверка актовности подарочной ссылки."""
        gift = await self._backend.get_gift_by_token(token)
        if not gift:
            return False
        # redeemable if not yet redeemed and not expired
        if gift.get("redeemed_at") or gift.get("recipient_tg_id"):
            return False
        return True

    async def register(self, token: str) -> Dict[str, Any]:
        gift = await self._backend.get_gift_by_token(token)
        if not gift:
            logger.warning("Подарочная ссылка не найдена", token=token)
            return {"success": False, "error": "gift_link_not_found"}

        return {
            "success": True,
            "type": "gift",
            "token": token,
            "tariff_id": gift.get("tariff_id"),
            "from_user_id": gift.get("sender_tg_id"),
        }
