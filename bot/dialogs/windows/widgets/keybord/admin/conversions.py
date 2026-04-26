"""Клавиатура окна конверсий."""

from aiogram_dialog.widgets.kbd import Column, SwitchTo
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import AdminManager


class AdminConversionsKeyboard(KeyboardBuilder):
    """Клавиатура с кнопкой «Назад» для экрана конверсий."""

    def build(self):
        return Column(
            SwitchTo(Const("🔙 Назад"), id="back_main", state=AdminManager.main),
        )
