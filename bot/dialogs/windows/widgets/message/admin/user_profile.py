from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminUserProfileMessage(MessageBuilder):
    """Message builder для профиля пользователя в админ-панели."""

    def build(self):
        return Format("{msg}")
