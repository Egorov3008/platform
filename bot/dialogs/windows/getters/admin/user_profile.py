from typing import Dict, Any, Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from models import User
from services.core.data.service import ServiceDataModel


class AdminUserProfileGetter(DataGetter):
    """Получает информацию профиля пользователя для админ-панели."""

    def __init__(self, model_data: ServiceDataModel):
        self.users = model_data.users
        self.keys = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает информацию профиля пользователя."""
        try:
            # Получаем tg_id из данных диалога или начальных данных
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

            # Получаем пользователя из кеша
            user: Optional[User] = await self.users.get_data(tg_id)

            if not user:
                logger.warning("Пользователь не найден", tg_id=tg_id)
                return {"msg": f"❌ Пользователь с ID {tg_id} не найден", "keys": []}

            # Получаем имя/username пользователя
            username = user.username if user.username else user.first_name

            # Получаем все ключи этого пользователя
            all_keys = await self.keys.get_all()
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            user_keys = [
                key for key in all_keys if hasattr(key, "tg_id") and key.tg_id == tg_id
            ]

            # Проверяем статус пробного периода
            trial_msg = "🔴 Использован" if user.trial == 0 else "🟢 Доступен"

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
                "username": user.username or "",
                "has_username": bool(user.username),
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении информации о пользователе",
                error=str(e),
                exc_info=True,
            )
            return {"msg": f"❌ Ошибка при загрузке профиля: {str(e)}", "keys": []}
