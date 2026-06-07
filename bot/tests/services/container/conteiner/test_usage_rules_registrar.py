"""Tests for UsageRulesRegistrar DI registration."""

import pytest
from punq import Container

from dialogs.windows.widgets.keybord.usage_rules.main import (
    UsageRulesMainKeyboard,
    UsageRulesPageKeyboard,
)
from dialogs.windows.widgets.message.usage_rules.main import (
    UsageRulesMainMessage,
    UsageRulesPageMessage,
)
from services.container.registrate.getters.usage_rules import UsageRulesRegistrar


@pytest.fixture
def bare_container():
    """Container without any registrations."""
    return Container()


class TestUsageRulesRegistrar:
    """Tests for UsageRulesRegistrar."""

    def test_register_keyboards(self, bare_container: Container):
        """UsageRulesRegistrar registers keyboard builders."""
        registrar = UsageRulesRegistrar()
        registrar.register_dependencies(bare_container)

        keyboard_main = bare_container.resolve(UsageRulesMainKeyboard)
        keyboard_page = bare_container.resolve(UsageRulesPageKeyboard)

        assert isinstance(keyboard_main, UsageRulesMainKeyboard)
        assert isinstance(keyboard_page, UsageRulesPageKeyboard)

    def test_register_messages(self, bare_container: Container):
        """UsageRulesRegistrar registers message builders."""
        registrar = UsageRulesRegistrar()
        registrar.register_dependencies(bare_container)

        message_main = bare_container.resolve(UsageRulesMainMessage)
        message_page = bare_container.resolve(UsageRulesPageMessage)

        assert isinstance(message_main, UsageRulesMainMessage)
        assert isinstance(message_page, UsageRulesPageMessage)

    def test_singletons(self, bare_container: Container):
        """UsageRulesRegistrar registers all classes as singletons."""
        registrar = UsageRulesRegistrar()
        registrar.register_dependencies(bare_container)

        keyboard_main_1 = bare_container.resolve(UsageRulesMainKeyboard)
        keyboard_main_2 = bare_container.resolve(UsageRulesMainKeyboard)

        assert keyboard_main_1 is keyboard_main_2, "Keyboard should be singleton"

        message_main_1 = bare_container.resolve(UsageRulesMainMessage)
        message_main_2 = bare_container.resolve(UsageRulesMainMessage)

        assert message_main_1 is message_main_2, "Message should be singleton"
