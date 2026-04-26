from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder
from dialogs.messages.users.gift.gift_activated import GIFT_KEY_ACTIVATED_MSG


class GiftKeyMessage(MessageBuilder):
    """Сообщение окна подарочного ключа."""

    def build(self) -> Text:
        return Format(GIFT_KEY_ACTIVATED_MSG)
