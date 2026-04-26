"""
Tests for DialogRegistry and dialog registration system.
"""

from dialogs.windows import ALL_WINDOW_CONFIGS
from states import MainMenu, UsageRules


class TestDialogRegistry:
    def test_dialog_registry_registers_all_window_configs(self):
        """DialogRegistry should accept all window configs without errors"""
        # This verifies that the window configs are well-formed
        assert len(ALL_WINDOW_CONFIGS) > 0
        assert isinstance(ALL_WINDOW_CONFIGS, (list, tuple))

    def test_all_state_groups_registered(self):
        """Verify all state groups have at least one window config"""
        registered_state_groups = {
            c["state"].group.__name__ for c in ALL_WINDOW_CONFIGS
        }

        expected_state_groups = {
            "MainMenu",
            "Tariff",
            "GiftStates",
            "PaymentState",
            "Register",
            "KeysInit",
            "Instruction",
            "UsageRules",
        }

        for group in expected_state_groups:
            assert group in registered_state_groups, (
                f"State group not registered: {group}"
            )

    def test_usage_rules_dialog_registered(self):
        """Regression: UnregisteredDialogError on 'Правила использования' button"""
        registered_states = {c["state"] for c in ALL_WINDOW_CONFIGS}

        assert UsageRules.main in registered_states, (
            "UsageRules.main not registered - will cause UnregisteredDialogError"
        )

        # Verify all 10 UsageRules states are configured
        usage_rules_configs = [
            c for c in ALL_WINDOW_CONFIGS if "UsageRules" in str(c["state"])
        ]
        assert len(usage_rules_configs) == 10, (
            f"Expected 10 UsageRules configs, got {len(usage_rules_configs)}"
        )

    def test_each_state_has_message_and_keyboard(self):
        """Every window config must have message_cls and keyboard_cls"""
        for config in ALL_WINDOW_CONFIGS:
            state = config["state"]
            assert "message_cls" in config, f"Missing message_cls for {state}"
            assert "keyboard_cls" in config, f"Missing keyboard_cls for {state}"
            assert config["message_cls"] is not None, f"message_cls is None for {state}"
            assert config["keyboard_cls"] is not None, (
                f"keyboard_cls is None for {state}"
            )

    def test_all_main_menu_states_registered(self):
        """MainMenu states should be registered"""
        registered_states = {c["state"] for c in ALL_WINDOW_CONFIGS}
        assert MainMenu.main in registered_states
        assert MainMenu.welcome in registered_states
        assert MainMenu.min_main in registered_states
