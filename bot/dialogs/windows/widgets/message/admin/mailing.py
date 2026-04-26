from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import MessageBuilder


class MailingInputMessage(MessageBuilder):
    """Сообщение ввода текста для массовой рассылки."""

    def build(self):
        return Const("✉️ Введите сообщение для рассылки:")


class MailingConfirmMessage(MessageBuilder):
    """Сообщение подтверждения отправки массовой рассылки."""

    def build(self):
        return Format(
            "📬 Вы уверены, что хотите отправить сообщение:\n\n<i>{text}</i>?"
        )
