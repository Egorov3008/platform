from typing import Dict, Any, Optional

from logger import logger
from models import GiftLink
from services.core.data.service import ServiceDataModel
from .base_registration import BaseRegistration


class GiftRegistration(BaseRegistration):
    def __init__(self, service: ServiceDataModel):
        super().__init__()
        self._gift_data = service.gifts

    async def can_handle(self, token: str) -> bool:
        """Проверка актовности подарочной ссылки."""
        gift_link: Optional[GiftLink] = await self._gift_data.get_by(token=token)
        if not gift_link:
            return False
        return gift_link.is_redeemable()

    async def register(self, token: str) -> Dict[str, Any]:
        gift_link: Optional[GiftLink] = await self._gift_data.get_by(token=token)
        if not gift_link:
            logger.warning("Подарочная ссылка не найдена", token=token)
            return {"success": False, "error": "gift_link_not_found"}

        return {
            "success": True,
            "type": "gift",
            "token": token,
            "tariff_id": gift_link.tariff_id,
            "from_user_id": gift_link.sender_tg_id,
        }
