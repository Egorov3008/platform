from typing import Dict, Any

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger


class TrialKeyGetter(DataGetter):
    """Геттер для окна с пробным/подарочным ключом."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        public_link = dialog_manager.start_data.get("public_link")
        link_to_connect = dialog_manager.start_data.get("link_to_connect")
        logger.debug(
            "Переход на окно ключа",
            public_link=public_link is not None,
            link_to_connect=link_to_connect is not None,
        )
        return {"public_link": public_link, "link_to_connect": link_to_connect}
