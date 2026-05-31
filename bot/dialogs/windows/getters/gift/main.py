from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from services.core.gift.repositories.gen_url import GiftUrlGenerator


class MainGetter(DataGetter):
    def __init__(self, backend: BackendAPIClient, url_service: GiftUrlGenerator):
        self.backend = backend
        self.url_service = url_service

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        tg_id = dialog_manager.event.from_user.id
        gifts = await self.backend.admin_list_gifts(sender_tg_id=tg_id)
        token = ""
        if gifts:
            token = gifts[0].get("token", "")
        url_gift = self.url_service.generate(token) if token else ""
        return {"link": url_gift}
