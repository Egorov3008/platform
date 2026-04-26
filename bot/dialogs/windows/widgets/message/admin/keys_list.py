"""Сообщения для окна списка ключей админ-панели."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminKeysListMessage(MessageBuilder):
    """Сообщение для окна списка ключей с сегментацией."""

    def build(self):
        return Format("{keys_message}")
