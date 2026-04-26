from typing import Dict, Any, Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models.keys.key import Key
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.keys.models.key_model import KeyModel
from models import Tariff


class KeyDetailsGetter(DataGetter):
    """Геттер для окна детального просмотра ключа."""


    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        email = dialog_manager.dialog_data.get("email")

        cache: CacheService = dialog_manager.middleware_data.get("cache") # type: ignore

        key: Optional[Key] = await cache.keys.get(CacheKeyManager.key(email))
        if not key:
            return {"error": True, "error_message": "❌ Ключ не найден"}
        tariff: Optional[Tariff] = await cache.tariffs.get(CacheKeyManager.tariff(key.tariff_id))
        return KeyModel(key, tariff).to_dict() # type: ignore
