from aiogram_dialog.widgets.kbd import Column, SwitchTo, Button
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import AdminManager
from getters.workers import delete_expired_keys_fast


class KeyStatsKeyboard(KeyboardBuilder):
    """Клавиатура общей статистики ключей."""

    def build(self):
        return Column(
            Button(
                Const("🗑️ Удалить старые ключи"),
                id="delete_keys",
                on_click=delete_expired_keys_fast,
            ),
            SwitchTo(
                Const("🔙 Назад"),
                id="back_to_main",
                state=AdminManager.main,
            ),
        )
