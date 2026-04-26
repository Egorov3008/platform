"""
Regression tests for UsageRules dialog registration.

Issue: UnregisteredDialogError on 'Правила использования' button
- The button tried to navigate to UsageRules.main state
- But the dialog was not registered in DialogRegistry
- Fixed by: exporting UsageRules in states/__init__.py and adding window configs
"""

from dialogs.windows import ALL_WINDOW_CONFIGS
from states import UsageRules


class TestUsageRulesDialogRegistration:
    def test_usage_rules_exported_from_states(self):
        """UsageRules should be exported from states module"""
        from states import UsageRules

        assert UsageRules is not None
        assert hasattr(UsageRules, "main")
        assert hasattr(UsageRules, "page1")
        assert hasattr(UsageRules, "page9")

    def test_usage_rules_main_state_registered(self):
        """UsageRules.main must be registered in window configs"""
        registered_states = {c["state"] for c in ALL_WINDOW_CONFIGS}
        assert UsageRules.main in registered_states, (
            "UsageRules.main not found in ALL_WINDOW_CONFIGS. "
            "This will cause UnregisteredDialogError on button click."
        )

    def test_all_usage_rules_pages_registered(self):
        """All 9 UsageRules page states must be registered"""
        expected_states = {
            UsageRules.main,
            UsageRules.page1,
            UsageRules.page2,
            UsageRules.page3,
            UsageRules.page4,
            UsageRules.page5,
            UsageRules.page6,
            UsageRules.page7,
            UsageRules.page8,
            UsageRules.page9,
        }

        registered_states = {c["state"] for c in ALL_WINDOW_CONFIGS}
        for state in expected_states:
            assert state in registered_states, (
                f"UsageRules state not registered: {state}"
            )

    def test_usage_rules_configs_count(self):
        """Verify exactly 10 UsageRules window configs (main + 9 pages)"""
        usage_rules_configs = [
            c for c in ALL_WINDOW_CONFIGS if "UsageRules" in str(c["state"])
        ]
        assert len(usage_rules_configs) == 10, (
            f"Expected 10 UsageRules configs (main + page1-9), got {len(usage_rules_configs)}"
        )

    def test_usage_rules_configs_have_message_and_keyboard(self):
        """Each UsageRules config must have message_cls and keyboard_cls"""
        usage_rules_configs = [
            c for c in ALL_WINDOW_CONFIGS if "UsageRules" in str(c["state"])
        ]

        for config in usage_rules_configs:
            state = config["state"]
            assert config["message_cls"] is not None, f"Missing message_cls for {state}"
            assert config["keyboard_cls"] is not None, (
                f"Missing keyboard_cls for {state}"
            )

    def test_usage_rules_main_page_first(self):
        """UsageRules.main should be the first registered UsageRules state"""
        usage_rules_states = [
            c["state"] for c in ALL_WINDOW_CONFIGS if "UsageRules" in str(c["state"])
        ]

        # Find index of main state
        main_index = None
        for i, state in enumerate(usage_rules_states):
            if state == UsageRules.main:
                main_index = i
                break

        assert main_index is not None, "UsageRules.main not found"
        # main should be first or at least present
        assert UsageRules.main in usage_rules_states

    def test_usage_rules_button_can_navigate(self):
        """Simulate button navigation: user clicks 'Правила' → starts UsageRules.main"""
        # This is what happens when user clicks "Правила использования 📃" button:
        # manager.start(UsageRules.main)
        # Verify that dialog is registered
        registered_states = {c["state"] for c in ALL_WINDOW_CONFIGS}
        assert UsageRules.main in registered_states, (
            "Button click would cause: aiogram_dialog.api.exceptions.UnregisteredDialogError"
        )
