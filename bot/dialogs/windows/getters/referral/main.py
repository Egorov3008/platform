from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from config import BOT_NAME
from dialogs.windows.base import DataGetter


class ReferralMainGetter(DataGetter):
    """Геттер для окна реферальной программы через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        tg_id = dialog_manager.event.from_user.id

        link = await self._backend.get_referral_link(tg_id)
        if link and link.token:
            share_url = f"https://t.me/{BOT_NAME}?start={link.token}"
            stats = await self._backend.get_referral_stats(tg_id)
            if not stats:
                stats = {}

            return {
                "has_link": True,
                "no_link": False,
                "share_url": share_url,
                "referral_count": stats.get("referral_count", 0),
                "rewards_count": stats.get("rewards_count", 0),
                "rewards_total": stats.get("rewards_total", 0.0),
                "available_balance": stats.get("balance", 0.0),
            }

        return {
            "has_link": False,
            "no_link": True,
            "share_url": "",
            "referral_count": 0,
            "rewards_count": 0,
            "rewards_total": 0.0,
            "available_balance": 0.0,
        }
