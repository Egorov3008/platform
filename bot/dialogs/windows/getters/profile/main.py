from typing import Dict, Any

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger
from models.users.user import User
from services.core.gift.repositories.checker import CheckerGiftLink
from services.core.user.utils.checked_admin import CheckedUser


class UserDataGetter(DataGetter):
    def __init__(
        self,
        backend_client: BackendAPIClient,
        checker_link: CheckerGiftLink,
        checked_user: CheckedUser,
    ):
        self._backend = backend_client
        self.checker_link = checker_link
        self.check_user = checked_user

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            tg_id = dialog_manager.event.from_user.id
            raw_user = await self._backend.get_user(tg_id)
            # BackendAPIClient.get_user returns a dict (not a model); convert
            # to User via the same tolerant factory used for keys.
            user: User | None = User.from_backend(raw_user) if raw_user else None
            keys = await self._backend.get_user_keys(tg_id)

            trial: bool = user.trial == 0 if user else True
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
                error=str(e),
                exc_info=True,
            )
            return {
                "username": f"ID{tg_id}" if "tg_id" in locals() else "unknown",
                "count_key": 0,
                "trial": True,
                "is_admin": False,
                "check_key": False,
                "check_usage_link": False,
            }
