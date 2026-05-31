from typing import Dict, Any, Optional

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger


class AdminUserProfileGetter(DataGetter):
    """Получает информацию профиля пользователя для админ-панели через Backend API."""

    def __init__(self, backend: BackendAPIClient):
        self.backend = backend

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает информацию профиля пользователя."""
        try:
            tg_id = None
            if dialog_manager.dialog_data:
                tg_id = dialog_manager.dialog_data.get("tg_id")
            if not tg_id and dialog_manager.start_data:
                tg_id = dialog_manager.start_data.get("tg_id")

            if not tg_id:
                logger.warning(
                    "Не получен tg_id при попытке отобразить профиль",
                    dialog_data=dialog_manager.dialog_data,
                    start_data=dialog_manager.start_data
                )
                return {"msg": "❌ Ошибка: не указан ID пользователя", "keys": []}

            logger.debug("Получаю информацию о пользователе", tg_id=tg_id)

            user = await self.backend.get_user(tg_id)
            if not user:
                logger.warning("Пользователь не найден", tg_id=tg_id)
                return {"msg": f"❌ Пользователь с ID {tg_id} не найден", "keys": []}

            username = user.get("username") or user.get("first_name") or ""
            user_keys = await self.backend.get_user_keys(tg_id)

            trial_msg = "🔴 Использован" if user.get("trial", 0) == 0 else "🟢 Доступен"

            msg = (
                f"📊 <b>Информация о пользователе</b>\n\n"
                f"🆔 <b>Telegram ID:</b> <code>{tg_id}</code>\n"
                f"👤 <b>Имя/Username:</b> <code>{username}</code>\n"
                f"🎯 <b>Пробный период:</b> {trial_msg}\n"
                f"🔑 <b>Количество ключей:</b> {len(user_keys)}"
            )

            logger.debug(
                "Профиль пользователя загружен", tg_id=tg_id, keys_count=len(user_keys)
            )

            return {
                "msg": msg,
                "keys": user_keys,
                "user_id": tg_id,
                "username": user.get("username") or "",
                "has_username": bool(user.get("username")),
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении информации о пользователе",
                error=str(e),
                exc_info=True,
            )
            return {"msg": f"❌ Ошибка при загрузке профиля: {str(e)}", "keys": []}
