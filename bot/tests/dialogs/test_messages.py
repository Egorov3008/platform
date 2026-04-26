from dialogs.messages.stats import STATS_MSG
from dialogs.messages.users.tariff.tariff import TARIFF_TEMPLATE
from dialogs.messages.users.welcom.first_msg import WELCOME_MSG
from dialogs.messages.users.gift.gift_activated import (
    GIFT_KEY_ACTIVATED_MSG,
    GIFT_ERROR,
)
from dialogs.messages.users.payments.payment import PAYMENT_INSTRUCTIONS
from dialogs.messages.users.rules.usage_rules import RULES_INTRO
from dialogs.messages.users.instructions.instructions import INSTRUCTIONS

MESSAGES = {
    "GIFT_ERROR": GIFT_ERROR,
    "GIFT_KEY_ACTIVATED_MSG": GIFT_KEY_ACTIVATED_MSG,
    "INSTRUCTIONS": INSTRUCTIONS,
    "payment_instructions": PAYMENT_INSTRUCTIONS,
    "tariffs_message": TARIFF_TEMPLATE,
    "STATS_MSG": STATS_MSG,
    "welcome_text": WELCOME_MSG,
    "rules_intro": RULES_INTRO,
}


def test_messages_structure():
    assert isinstance(MESSAGES, dict)
    assert len(MESSAGES) > 0


def test_messages_keys():
    expected_keys = [
        "GIFT_ERROR",
        "GIFT_KEY_ACTIVATED_MSG",
        "INSTRUCTIONS",
        "payment_instructions",
        "tariffs_message",
        "STATS_MSG",
        "welcome_text",
        "rules_intro",
    ]

    for key in expected_keys:
        assert key in MESSAGES, f"Key {key} not found in MESSAGES"


def test_messages_values():
    for key, value in MESSAGES.items():
        assert isinstance(value, str), f"Value for {key} is not a string"
        assert len(value) > 0, f"Value for {key} is empty"


def test_stats_message_formatting():
    stats_message = MESSAGES["STATS_MSG"]
    assert "{users}" in stats_message
    assert "{keys}" in stats_message
    assert "{revenue}" in stats_message

    formatted = stats_message.format(users=100, keys=50, revenue=5000)
    assert "100" in formatted
    assert "50" in formatted
    assert "5000" in formatted


def test_tariffs_message_content():
    tariffs_message = MESSAGES["tariffs_message"]
    assert "🚀 ДОСТУПНЫЕ ТАРИФЫ" in tariffs_message
    assert "{{ tariff.amount }}" in tariffs_message
    assert "{% for tariff in tariffs %}" in tariffs_message


def test_welcome_message_content():
    welcome_text = MESSAGES["welcome_text"]
    assert "<b>" in welcome_text
    assert "Добро пожаловать" in welcome_text
    assert len(welcome_text) > 10
