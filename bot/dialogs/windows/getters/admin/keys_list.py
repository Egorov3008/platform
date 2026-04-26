"""
Геттер для отображения списка ключей с сегментацией и пагинацией.
"""

from typing import Dict, Any, Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import Key
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.keys.segmentation import KeySegmentationService
from services.core.keys.models.key_model import KeyModel
from logger import logger


class AdminKeyListGetter(DataGetter):
    """Геттер для отображения отфильтрованного списка ключей."""

    def __init__(self, model_data: ServiceDataModel):
        self.keys = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """
        Получить список ключей текущего сегмента.

        Использует текущий сегмент из dialog_data['current_segment'].
        Для сегментов expiring_* используется фильтрация по времени.
        """
        try:
            all_keys = await self.keys.get_all()

            # Нормализуем в список
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            # Получаем текущий сегмент из dialog_data
            current_segment = dialog_manager.dialog_data.get("current_segment", "all")

            # Для сегментов expiring_* используем фильтрацию по времени
            segmentation = KeySegmentationService()
            if current_segment == "expiring_24h":
                filtered_keys = await segmentation.get_expiring_24h(all_keys)
            elif current_segment == "expiring_7d":
                filtered_keys = await segmentation.get_expiring_7d(all_keys)
            elif current_segment == "expiring_30d":
                filtered_keys = await segmentation.get_expiring_30d(all_keys)
            else:
                # Для остальных сегментов используем filter_by_name
                filtered_keys = await segmentation.filter_by_name(
                    all_keys, current_segment
                )

            # Сохраняем в dialog_data для использования в Select и обработчиках
            dialog_manager.dialog_data["filtered_keys"] = filtered_keys
            dialog_manager.dialog_data["total_filtered"] = len(filtered_keys)

            # Подготавливаем данные для Select виджета (email, объект ключа)
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
                "keys": filtered_keys,  # Для key_selector() из widgets/keybord.py
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
                "total_keys": 0,
            }


class AdminKeyDetailsGetter(DataGetter):
    """Геттер для отображения деталей ключа.

    Использует KeyModel для получения стандартных полей KeyDetailsMessage
    и добавляет дополнительные admin-специфичные поля.
    """

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить детали выбранного ключа.

        Возвращает объединение KeyModel.to_dict() (для KeyDetailsMessage)
        и дополнительных admin-полей.
        """
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            key: Optional[Key] = dialog_manager.start_data.get("selected_key") if dialog_manager.start_data else dialog_manager.dialog_data.get("selected_key")  
            
            
            if not key:
                return {"error": True}

            # Получаем тариф из кеша
            tariff = await cache.tariffs.get(CacheKeyManager.tariff(key.tariff_id))
            if not tariff:
                return {"error": True}

            # Создаём KeyModel и получаем стандартные поля
            key_model = KeyModel(key, tariff)
            data = key_model.to_dict()
            
            dialog_manager.dialog_data["selected_key"] = key
            # Добавляем дополнительные admin-специфичные поля
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
