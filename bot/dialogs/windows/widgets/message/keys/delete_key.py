from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


class DeleteKeyMessage(MessageBuilder):
    """Сообщение окна подтверждения удаления ключа."""

    def build(self) -> Text:
        return Format("Вы уверены, что хотите удалить ключ {email}?")
