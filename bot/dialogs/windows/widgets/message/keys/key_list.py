from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


class KeyListMessage(MessageBuilder):
    """Сообщение окна списка ключей."""

    def build(self) -> Text:
        return Format("{msg}")
