from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Row, Button, Back
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import MainMenu


class DeleteKeyKeyboard(KeyboardBuilder):
    """Клавиатура окна подтверждения удаления ключа."""

    def __init__(self, backend_client: BackendAPIClient) -> None:
        self._backend = backend_client

    async def _delete_key(
        self,
        callback: CallbackQuery,
        button: Any,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Удаление ключа через backend API."""
        email = dialog_manager.dialog_data.get("email")
        tg_id = callback.from_user.id

        logger.debug("Удаление ключа через backend API", email=email, tg_id=tg_id)
        success = await self._backend.delete_key(email, tg_id)

        if not success:
            await callback.answer("❌ Не удалось удалить ключ", show_alert=True)
            return

        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
        await callback.answer(f"Ключ {email} удалён 🆗", show_alert=True)

    def build(self):
        return Row(
            Button(Const("Да"), id="confirm_delete", on_click=self._delete_key),
            Back(Const("Нет")),
        )
