from aiogram_dialog.widgets.kbd import CopyText, Start, Column
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from states import MainMenu


class GiftMainKeyboard(KeyboardBuilder):
    def build(self):
        return Column(
            CopyText(Const("📋 Скопировать ссылку"), copy_text=Format("{link}")),
            Start(Const("👤 В личный кабинет"), id="profile", state=MainMenu.main),
        )
