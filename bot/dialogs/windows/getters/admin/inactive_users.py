"""Геттер для поиска неактивных пользователей через backend API."""

from typing import Dict, Any

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger


class InactiveUsersGetter(DataGetter):
    """Находит пользователей с is_blocked=True и без ключей через backend."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Возвращает список неактивных пользователей и их количество."""
        try:
            result = await self._backend.admin_list_inactive_users()
            users = result.get("users", [])
            dialog_manager.dialog_data["inactive_users"] = users

            return {
                "inactive_users_count": result.get("count", 0),
                "inactive_users": users,
            }

        except Exception as e:
            logger.error(
                "Ошибка при поиске неактивных пользователей",
                error=str(e),
                exc_info=True,
            )
            return {"inactive_users_count": 0, "inactive_users": []}
