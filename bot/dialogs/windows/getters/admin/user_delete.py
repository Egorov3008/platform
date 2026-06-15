"""Геттер для окна подтверждения удаления пользователя."""

from typing import Dict, Any

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger
from models.users.user import User


class AdminUserDeleteGetter(DataGetter):
    """Геттер для окна подтверждения удаления пользователя через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить данные пользователя для отображения при удалении."""
        try:
            tg_id = dialog_manager.start_data.get("tg_id")
            if not tg_id:
                return {"tg_id": "", "username": "", "keys_count": 0}

            raw_user = await self._backend.get_user(tg_id)
            # get_user returns a dict from the backend; normalize to User.
            user: User | None = User.from_backend(raw_user) if raw_user else None
            if not user:
                return {"tg_id": tg_id, "username": "Не найден", "keys_count": 0}

            username = user.username or user.first_name or ""
            keys = await self._backend.get_user_keys(tg_id)

            return {
                "tg_id": tg_id,
                "username": username,
                "keys_count": len(keys),
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении данных пользователя для удаления",
                error=str(e),
                exc_info=True,
            )
            return {"tg_id": "", "username": "", "keys_count": 0}
