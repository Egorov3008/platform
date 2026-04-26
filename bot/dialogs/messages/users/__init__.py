from dialogs.messages.users.gift.gift_activated import (
    GIFT_KEY_ACTIVATED_MSG,
    GIFT_ERROR,
    GIFT_SUCCESS,
)

# Импорт error_messages, используемый в middleware
from dialogs.messages.users.error_msg.bot_errors import error_messages
from .instructions.instructions import (
    INSTRUCTIONS,
    INSTRUCTION_PC,
    IPHONE_INSTRUCTION,
    LINUX_INSTRUCTION,
    ANDROID_INSTRUCTION,
    WINDOWS_INSTRUCTION,
)
from .payments.payment import PAYMENT_INSTRUCTIONS
from .profile.main_menu import MENU_MESSAGE, MIN_MENU_MESSAGE
from .reminder.discount_reminder import DISCOUNT_REMINDER_MESSAGE
from .rules.usage_rules import USAGE_RULES, RULES_INTRO
from .tariff.tariff import TARIFF_TEMPLATE
from .welcom.first_msg import MSG_PREVIEW, WELCOME_MSG, SENDING_REGISTRATION


__all__ = (
    "MENU_MESSAGE",
    "MIN_MENU_MESSAGE",
    "PAYMENT_INSTRUCTIONS",
    "INSTRUCTIONS",
    "INSTRUCTION_PC",
    "IPHONE_INSTRUCTION",
    "LINUX_INSTRUCTION",
    "ANDROID_INSTRUCTION",
    "WINDOWS_INSTRUCTION",
    "GIFT_KEY_ACTIVATED_MSG",
    "GIFT_ERROR",
    "GIFT_SUCCESS",
    "SENDING_REGISTRATION",
    "error_messages",
)
