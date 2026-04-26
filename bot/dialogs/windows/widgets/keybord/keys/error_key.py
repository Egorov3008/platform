from aiogram_dialog.widgets.kbd import Keyboard, Start
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import MainMenu


class ErrorKeyKeyboard(KeyboardBuilder):
    """Клавиатура для окна ошибки при создании ключа."""

    def build(self) -> Keyboard:
        return Start(
            Const("📍 Вернуться в меню"),
            id="back_to_menu",
            state=MainMenu.main,
        )
