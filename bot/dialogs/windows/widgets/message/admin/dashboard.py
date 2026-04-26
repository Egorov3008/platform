"""Message builder для окна Dashboard."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminDashboardMessage(MessageBuilder):
    """Формирует сообщение для окна Dashboard."""

    def build(self) -> Format:
        return Format("{DASHBOARD_MSG}")
