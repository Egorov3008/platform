"""Геттер для поиска неактивных пользователей (заблокировали бота и нет ключей)."""

from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from models import User, Key
from services.core.data.service import ServiceDataModel


class InactiveUsersGetter(DataGetter):
    """Находит пользователей с is_blocked=True и без ключей."""

    def __init__(self, model_data: ServiceDataModel):
        self.users_data = model_data.users
        self.keys_data = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Возвращает список неактивных пользователей и их количество."""
        try:
            all_users = await self.users_data.get_all()
            all_keys = await self.keys_data.get_all()

            if not isinstance(all_users, list):
                all_users = [all_users] if all_users else []
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            # Собираем tg_id пользователей, у которых есть ключи
            users_with_keys = {k.tg_id for k in all_keys if isinstance(k, Key)}

            # Фильтруем: is_blocked=True И нет ключей
            inactive_users: List[User] = [
                u for u in all_users
                if isinstance(u, User)
                and u.is_blocked
                and u.tg_id not in users_with_keys
            ]

            # Сохраняем для последующего удаления
            dialog_manager.dialog_data["inactive_users"] = inactive_users

            return {
                "inactive_users_count": len(inactive_users),
                "inactive_users": inactive_users,
            }

        except Exception as e:
            logger.error(
                "Ошибка при поиске неактивных пользователей",
                error=str(e),
                exc_info=True,
            )
            return {"inactive_users_count": 0, "inactive_users": []}
