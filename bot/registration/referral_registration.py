from typing import Dict, Any, Optional

from logger import logger
from models import ReferralLink
from services.core.data.service import ServiceDataModel
from .base_registration import BaseRegistration


class ReferralRegistration(BaseRegistration):
    """Обработка регистрации по реферальной ссылке."""

    def __init__(self, service: ServiceDataModel):
        super().__init__()
        self._referral_data = service.referral_links

    async def can_handle(self, token: str) -> bool:
        """Проверяет, является ли токен реферальной ссылкой."""
        link: Optional[ReferralLink] = await self._referral_data.get_by(token=token)
        return link is not None

    async def register(self, token: str) -> Dict[str, Any]:
        """Возвращает данные для регистрации по реферальной ссылке."""
        link: Optional[ReferralLink] = await self._referral_data.get_by(token=token)
        if not link:
            logger.warning("Реферальная ссылка не найдена", token=token)
            return {"success": False, "error": "referral_link_not_found"}

        return {
            "success": True,
            "type": "referral",
            "token": token,
            "referrer_tg_id": link.referrer_tg_id,
            "referral_link_id": link.id,
        }
