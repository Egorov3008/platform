from aiogram_dialog.widgets.kbd import Column, Url, CopyText, Start
from aiogram_dialog.widgets.text import Const, Format

from config import SUPPORT_CHAT_URL
from dialogs.windows.base import KeyboardBuilder
from states import MainMenu


class GiftKeyKeyboard(KeyboardBuilder):
    """Клавиатура окна подарочного ключа."""

    def build(self):
        return Column(
            Url(
                Const("🔗 Вставить ключ в приложение"),
                id="link_gift",
                url=Format("{link_to_connect}"),
            ),
            CopyText(Const("📋 Скопировать ключ"), copy_text=Format("{public_link}")),
            Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
            Start(Const("👤 Личный кабинет"), id="profile_gift", state=MainMenu.main),
        )
