"""Геттер для окна подтверждения удаления пользователя."""

from typing import Dict, Any, Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from models import User
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService


class AdminUserDeleteGetter(DataGetter):
    """Геттер для окна подтверждения удаления пользователя."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить данные пользователя для отображения при удалении."""
        try:
            cache: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
            tg_id = dialog_manager.start_data.get("tg_id")

            if not tg_id or not cache:
                return {"tg_id": "", "username": "", "keys_count": 0}

            user: Optional[User] = await cache.users.get(CacheKeyManager.user(tg_id))
            if not user:
                return {"tg_id": tg_id, "username": "Не найден", "keys_count": 0}

            username = user.username if user.username else user.first_name

            # Подсчитать ключи пользователя
            all_keys = await cache.keys.all()
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            keys_count = len(
                [k for k in all_keys if hasattr(k, "tg_id") and k.tg_id == tg_id]
            )

            return {
                "tg_id": tg_id,
                "username": username or "",
                "keys_count": keys_count,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении данных пользователя для удаления",
                error=str(e),
                exc_info=True,
            )
            return {"tg_id": "", "username": "", "keys_count": 0}
