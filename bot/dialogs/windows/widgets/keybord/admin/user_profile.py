from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Column, Button, Url, Cancel, Group
from aiogram_dialog.widgets.text import Const, Jinja

from dialogs.windows.base import KeyboardBuilder
from getters.on_click.admin_click import on_click_restore_trial
from states import AdminUserDeleteSG
from widgets.keybord import key_selector


class AdminUserProfileKeyboard(KeyboardBuilder):
    """Клавиатура для профиля пользователя в админ-панели."""

    def build(self):
        return Group(
            Column(
                key_selector(),
                Url(
                    Const("💬 Написать пользователю"),
                    url=Jinja("https://t.me/{{ username }}"),
                    when="has_username",
                ),
                Button(
                    Const("🔄 Восстановить пробник"),
                    id="restore_trial",
                    on_click=on_click_restore_trial,
                ),
                Button(
                    Const("❌ Удалить клиента"),
                    id="confirm_delete_user",
                    on_click=self._on_delete_click,
                ),
                Cancel(Const("🔙 Назад")),
            ),
        )

    @staticmethod
    async def _on_delete_click(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Переход на экран подтверждения удаления пользователя."""
        dialog_data = (
            manager.dialog_data if isinstance(manager.dialog_data, dict) else {}
        )
        start_data = (
            manager.start_data if isinstance(manager.start_data, dict) else {}
        )
        tg_id = dialog_data.get("tg_id") or start_data.get("tg_id")

        if not tg_id:
            await callback.answer("❌ Пользователь не указан", show_alert=True)
            return

        await manager.start(
            AdminUserDeleteSG.confirm,
            data={"tg_id": tg_id},
            mode=StartMode.NORMAL,
        )
