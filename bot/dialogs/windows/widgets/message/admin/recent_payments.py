from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class RecentPaymentsMessage(MessageBuilder):
    """Сообщение с платежами за текущие сутки."""

    def build(self):
        return Format("{RECENT_PAY_MSG}")
