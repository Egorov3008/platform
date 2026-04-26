from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class KeyStatsMessage(MessageBuilder):
    """Сообщение общей статистики ключей."""

    def build(self):
        return Format("{STATS_MSG}")
