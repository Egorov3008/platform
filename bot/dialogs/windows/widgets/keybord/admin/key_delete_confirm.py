"""Клавиатура для подтверждения удаления ключа."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Column, Button, Cancel
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminManager


class AdminKeyDeleteConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления ключа."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete",
                on_click=self._on_confirm,
            ),
            Cancel(Const("🔙 Отмена")),
        )

    @staticmethod
    async def _on_confirm(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Удалить ключ через backend API."""
        email = manager.start_data.get("email")

        if not email:
            await callback.answer("❌ Email ключа не передан", show_alert=True)
            return

        try:
            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)
            success = await backend.admin_delete_key(email)

            if not success:
                await callback.answer("❌ Не удалось удалить ключ", show_alert=True)
                return

            logger.info("Ключ удалён администратором через backend", email=email)
            await callback.answer(f"✅ Ключ {email} успешно удалён", show_alert=True)
            await manager.start(AdminManager.key_list, mode=StartMode.RESET_STACK)

        except Exception as e:
            logger.error(
                "Ошибка при удалении ключа администратором",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
