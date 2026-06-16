"""
Геттер для отображения списка ключей с сегментацией и пагинацией.
"""

from typing import Dict, Any, List, Optional

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models import Key, Tariff
from services.core.keys.segmentation import KeySegmentationService
from services.core.keys.models.key_model import KeyModel
from logger import logger


class AdminKeyListGetter(DataGetter):
    """Геттер для отображения отфильтрованного списка ключей через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        current_segment = dialog_manager.dialog_data.get("current_segment", "all")
        try:
            raw_keys = await self._backend.admin_list_keys()
            all_keys = [Key.from_backend(k) for k in raw_keys]

            segmentation = KeySegmentationService()
            if current_segment == "expiring_24h":
                filtered_keys = await segmentation.get_expiring_24h(all_keys)
            elif current_segment == "expiring_7d":
                filtered_keys = await segmentation.get_expiring_7d(all_keys)
            elif current_segment == "expiring_30d":
                filtered_keys = await segmentation.get_expiring_30d(all_keys)
            else:
                filtered_keys = await segmentation.filter_by_name(all_keys, current_segment)

            dialog_manager.dialog_data["filtered_keys"] = filtered_keys
            dialog_manager.dialog_data["total_filtered"] = len(filtered_keys)

            keys_data = [(f"{key.email} {key.tg_id}", key) for key in filtered_keys]

            segment_title = {
                "expiring_24h": "⏰ Истекают в 24 часа",
                "expiring_7d": "📅 Истекают в 7 дней",
                "expiring_30d": "📆 Истекают в 30 дней",
                "expired": "🔴 Истёкшие ключи",
                "active": "✅ Активные ключи",
                "trial": "🎯 Trial ключи",
                "unused": "📵 Неиспользуемые ключи",
                "all": "🔹 Все ключи",
            }

            message = (
                f"<b>{segment_title.get(current_segment, current_segment)}</b>\n\n"
                f"Найдено ключей: <b>{len(filtered_keys)}</b>\n\n"
                f"Выберите ключ из списка ниже для просмотра деталей и администрирования:"
            )

            return {
                "keys_message": message,
                "keys_data": keys_data,
                "keys": filtered_keys,
                "total_keys": len(filtered_keys),
                "segment": current_segment,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении списка ключей", error=str(e), exc_info=True
            )
            return {
                "keys_message": f"❌ Ошибка при загрузке ключей: {str(e)}",
                "keys_data": [],
                "keys": [],
                "total_keys": 0,
                "segment": current_segment,
            }


class AdminKeyDetailsGetter(DataGetter):
    """Геттер для отображения деталей ключа через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            key: Optional[Key] = dialog_manager.start_data.get("selected_key") if dialog_manager.start_data else dialog_manager.dialog_data.get("selected_key")
            if not key:
                return {"error": True}

            tariff = await self._backend.get_tariff(key.tariff_id)
            if not tariff:
                return {"error": True}

            tariff = Tariff.from_dict(tariff)
            key_model = KeyModel(key, tariff)
            data = key_model.to_dict()

            dialog_manager.dialog_data["selected_key"] = key
            data.update({
                "tg_id": key.tg_id,
                "client_id": key.client_id,
                "inbound_id": key.inbound_id,
                "created_at": key.created_at,
            })

            return data

        except Exception as e:
            logger.error(
                "Ошибка при получении деталей ключа", error=str(e), exc_info=True
            )
            return {"error": True}
