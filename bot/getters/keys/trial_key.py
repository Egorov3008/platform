from typing import Optional, Dict, Any

from aiogram_dialog import DialogManager
from logger import logger


async def getter_trial_key(
    dialog_manager: DialogManager, **_kwargs
) -> Optional[Dict[str, Any]]:
    """Геттер для пробного ключа"""
    public_link = dialog_manager.start_data.get("public_link")
    link_to_connect = dialog_manager.start_data.get("link_to_connect")
    logger.debug(
        "Переход на создание пробного ключа",
        public_link=public_link is not None,
        link_to_connect=link_to_connect is not None,
    )
    return {"public_link": public_link, "link_to_connect": link_to_connect}
