from typing import Dict, Any

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter


class ConfirmDeleteKeyGetter(DataGetter):
    """Геттер для окна подтверждения удаления ключа."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        email = dialog_manager.dialog_data.get("email")
        return {"email": email}
