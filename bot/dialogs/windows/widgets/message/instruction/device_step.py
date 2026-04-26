from aiogram_dialog.widgets.text import Const, Text

from dialogs.windows.base import MessageBuilder


class InstructionDeviceMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "Скачайте приложение для вашего устройства.\n"
            "После чего перейдите к следующему шагу инструкции 👇"
        )
