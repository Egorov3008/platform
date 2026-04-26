from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from models import Key
from services.core.data.service import ServiceDataModel


class KeyListGetter(DataGetter):
    """Геттер для окна списка ключей пользователя."""

    def __init__(self, model_data: ServiceDataModel):
        self.key_data = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            tg_id = dialog_manager.event.from_user.id
            
            # Сначала пробуем получить ключи из кеша
            result = await self.key_data.get_by(tg_id=tg_id)
            
            keys: List[Key] = (
                result if isinstance(result, list) else ([result] if result else [])
            )
            
            # Если ключей нет в кеше, пробуем загрузить из БД
            if not keys:
                logger.info(
                    "Ключи не найдены в кеше, загрузка из БД",
                    tg_id=tg_id,
                )
                pool = dialog_manager.middleware_data.get("pool")
                if pool:
                    # Загружаем все ключи из БД и фильтруем по tg_id
                    db_keys = await self.key_data.service.get_all(pool)
                    keys = [k for k in db_keys if k.tg_id == tg_id]
                    
                    # Сохраняем найденные ключи в кеш
                    for key in keys:
                        cache_key = f"key_{key.email}"
                        await self.key_data.cache_service.keys.set(cache_key, key)
                    
                    logger.info(
                        "Загружено ключей из БД",
                        tg_id=tg_id,
                        count=len(keys),
                    )

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
                tg_id=dialog_manager.event.from_user.id if hasattr(dialog_manager, 'event') and hasattr(dialog_manager.event, 'from_user') else 'unknown',
                error=str(e),
                exc_info=True,
            )
            return {"msg": "❌ Ошибка при загрузке ключей", "key_data": []}
