from aiogram_dialog.widgets.kbd import Keyboard, Cancel
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder


class CancelKeyboard(KeyboardBuilder):
    def build(self) -> Keyboard:
        return Cancel(text=Const("Назад"))
