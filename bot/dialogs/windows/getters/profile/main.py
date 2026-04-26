from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from models import Key, User
from services.core.data.service import ServiceDataModel
from services.core.gift.repositories.checker import CheckerGiftLink
from services.core.user.utils.checked_admin import CheckedUser


class UserDataGetter(DataGetter):
    def __init__(
        self,
        model_data: ServiceDataModel,
        checker_link: CheckerGiftLink,
        checked_user: CheckedUser,
    ):
        self.user_data = model_data.users
        self.key_data = model_data.keys
        self.checker_link = checker_link
        self.check_user = checked_user

    async def _get_keys(self, tg_id: int, pool=None) -> List[Key]:
        """Получает ключи пользователя из кеша или БД."""
        # Сначала пробуем получить из кеша
        keys_result = await self.key_data.get_by(tg_id=tg_id)
        
        if keys_result is None:
            keys = []
        elif isinstance(keys_result, list):
            keys = keys_result
        else:
            keys = [keys_result]
        
        # Если ключей нет в кеше, пробуем загрузить из БД
        if not keys and pool:
            logger.info(
                "Ключи не найдены в кеше, загрузка из БД",
                tg_id=tg_id,
            )
            try:
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
            except Exception as e:
                logger.error(
                    "Ошибка при загрузке ключей из БД",
                    tg_id=tg_id,
                    error=str(e),
                )
        
        return keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            tg_id = dialog_manager.event.from_user.id
            user: User = await self.user_data.get_data(tg_id)
            trial: bool = user.trial == 0 if user else True
            
            # Получаем пул соединений для загрузки из БД
            pool = dialog_manager.middleware_data.get("pool")
            keys = await self._get_keys(tg_id, pool)
            
            count_key = len(keys)
            is_admin = self.check_user.check(tg_id)
            check_key = count_key > 0
            check_usage_link = await self.checker_link.check(tg_id)

            return {
                "username": (user.username if user else None) or f"ID{tg_id}",
                "count_key": count_key,
                "trial": trial,
                "is_admin": is_admin,
                "check_key": check_key,
                "check_usage_link": check_usage_link,
            }
        except Exception as e:
            logger.error(
                "Ошибка при получении данных пользователя",
                tg_id=dialog_manager.event.from_user.id if hasattr(dialog_manager, 'event') and hasattr(dialog_manager.event, 'from_user') else 'unknown',
                error=str(e),
                exc_info=True,
            )
            return {
                "username": f"ID{tg_id}" if 'tg_id' in locals() else "unknown",
                "count_key": 0,
                "trial": True,
                "is_admin": False,
                "check_key": False,
                "check_usage_link": False,
            }
