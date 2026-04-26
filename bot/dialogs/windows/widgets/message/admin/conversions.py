"""Сообщение окна конверсий."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminConversionsMessage(MessageBuilder):
    """Отображает метрики конверсий пользователей."""

    def build(self):
        return Format("{CONVERSIONS_MSG}")
