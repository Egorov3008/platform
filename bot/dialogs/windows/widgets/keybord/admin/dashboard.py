"""Keyboard builder для окна Dashboard."""

from aiogram_dialog.widgets.kbd import Column, Back, Button
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder


class AdminDashboardKeyboard(KeyboardBuilder):
    """Клавиатура для окна Dashboard."""

    async def _on_toggle_notifications(self, callback, button, manager):
        """Обработчик переключения уведомлений."""
        from handlers.admin import toggle_notifications
        await toggle_notifications(callback, button, manager)

    def build(self) -> Column:
        return Column(
            Button(
                Format("{notifications_status}"),
                id="toggle_notifications",
                on_click=self._on_toggle_notifications,
            ),
            Back(text=Const("◀️ Назад")),
        )
