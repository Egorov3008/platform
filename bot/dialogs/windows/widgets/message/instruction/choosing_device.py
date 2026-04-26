from aiogram_dialog.widgets.text import Const, Text

from dialogs.windows.base import MessageBuilder


class InstructionChoosingMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "Давайте настроим ваше устройство к работе с нашим сервисом!\n"
            "Выберете устройство 📱💻"
        )
