from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from api.schemas import KeyDTO
from dialogs.windows.base import DataGetter
from logger import logger


class KeyListGetter(DataGetter):
    """Геттер для окна списка ключей пользователя."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            tg_id = dialog_manager.event.from_user.id
            keys: List[KeyDTO] = await self._backend.get_user_keys(tg_id)

            key_data = []
            for i, key in enumerate(keys):
                dialog_manager.dialog_data[str(i)] = key.email
                key_data.append((i, key.email))

            msg = (
                "<b>🔑 Список ваших устройств</b>\n\n<i>👇 Выберите ключ для управления подпиской:</i>"
                if keys
                else "❌ Ключи не найдены"
            )
            return {"msg": msg, "key_data": key_data}

        except Exception as e:
            logger.error(
                "Ошибка при получении списка ключей",
                tg_id=getattr(getattr(dialog_manager, "event", None), "from_user", {}) and dialog_manager.event.from_user.id,
                error=str(e),
                exc_info=True,
            )
            return {"msg": "❌ Ошибка при загрузке ключей", "key_data": []}
