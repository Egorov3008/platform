from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import MessageBuilder


class AdminMainMessage(MessageBuilder):
    """Сообщение главной панели администратора."""

    def build(self):
        return Const("🤖 Панель администратора")


class AdminStatsMessage(MessageBuilder):
    """Сообщение статистики администратора."""

    def build(self):
        return Format("{STATS_MSG}")
