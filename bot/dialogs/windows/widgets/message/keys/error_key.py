from aiogram_dialog.widgets.text import Text, Const

from dialogs.windows.base import MessageBuilder


class ErrorKeyMessage(MessageBuilder):
    """Сообщение окна ошибки при создании ключа."""

    def build(self) -> Text:
        return Const(
            "❌ Произошла ошибка при создании ключа.\n\n"
            "Пожалуйста, обратитесь в поддержку для решения проблемы."
        )
