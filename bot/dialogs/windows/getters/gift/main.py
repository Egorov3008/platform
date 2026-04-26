from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import GiftLink
from services.core.data.service import ServiceDataModel
from services.core.gift.repositories.gen_url import GiftUrlGenerator


class MainGetter(DataGetter):
    def __init__(self, model_data: ServiceDataModel, url_service: GiftUrlGenerator):
        self.gift_service = model_data.gifts
        self.url_service = url_service

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        tg_id = dialog_manager.event.from_user.id
        gift: GiftLink = await self.gift_service.get_data(tg_id)
        url_gift = self.url_service.generate(gift.token)
        return {"link": url_gift}
