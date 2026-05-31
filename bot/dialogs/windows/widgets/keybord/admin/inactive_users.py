"""Клавиатуры для модуля очистки неактивных пользователей."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Button, SwitchTo, Cancel, Start
from aiogram_dialog.widgets.text import Const
from aiogram_dialog import StartMode

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminManager, AdminUserCleanupSG


class InactiveUsersReviewKeyboard(KeyboardBuilder):
    """Клавиатура обзора неактивных пользователей."""

    def build(self):
        return Column(
            Start(
                Const("🗑️ Удалить неактивных"),
                id="delete_inactive",
                state=AdminUserCleanupSG.confirm,
            ),
            Start(Const("🔙 Назад"), id="back_main", state=AdminManager.main, mode=StartMode.RESET_STACK),
        )


class InactiveUsersConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления неактивных пользователей."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete_inactive",
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
        """Удалить всех неактивных пользователей через backend API."""
        inactive_users: list = manager.dialog_data.get("inactive_users", [])

        if not inactive_users:
            await callback.answer(
                "❌ Нет пользователей для удаления", show_alert=True
            )
            return

        container = manager.middleware_data.get("container")
        if not container:
            await callback.answer("❌ Ошибка: не удалось получить DI контейнер", show_alert=True)
            return

        try:
            backend = container.resolve(BackendAPIClient)
            result = await backend.admin_delete_inactive_users()
            deleted_count = result.get("deleted", 0)

            logger.info("Удалены неактивные пользователи через backend", count=deleted_count)

            await callback.answer(
                f"✅ Удалено {deleted_count} неактивных пользователей",
                show_alert=True,
            )

            await manager.start(AdminManager.main)

        except Exception as e:
            logger.error(
                "Ошибка при удалении неактивных пользователей",
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
