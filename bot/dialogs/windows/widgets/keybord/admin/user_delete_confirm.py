"""Клавиатура для подтверждения удаления пользователя."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Button, Cancel
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminManager


class AdminUserDeleteConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления пользователя."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete_user",
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
        """Удалить пользователя через backend API."""
        tg_id = manager.start_data.get("tg_id")

        if not tg_id:
            await callback.answer("❌ ID пользователя не передан", show_alert=True)
            return

        container = manager.middleware_data.get("container")
        if not container:
            await callback.answer("❌ Ошибка: не удалось получить DI контейнер", show_alert=True)
            return

        try:
            backend = container.resolve(BackendAPIClient)
            success = await backend.admin_delete_user(tg_id)
            if not success:
                await callback.answer("❌ Не удалось удалить пользователя", show_alert=True)
                return

            logger.info("Пользователь удалён из системы через backend", tg_id=tg_id)
            await callback.answer(
                f"✅ Пользователь {tg_id} успешно удален из системы", show_alert=True
            )
            await manager.start(AdminManager.main)

        except Exception as e:
            logger.error("Ошибка при удалении пользователя", tg_id=tg_id, error=str(e))
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
