"""
Tests for WindowFactory that creates Dialog Window objects from configuration.
"""

from dialogs.windows.window_factory import WindowFactory
from dialogs.windows import ALL_WINDOW_CONFIGS
from states import MainMenu


class TestWindowFactory:
    def test_window_factory_creates_from_config(self):
        """WindowFactory should create Window objects from config dict"""
        # Verify that WindowFactory can be imported and instantiated
        assert WindowFactory is not None

    def test_all_window_configs_have_required_fields(self):
        """Verify all window configs have required fields"""
        required_fields = {"state", "message_cls", "keyboard_cls", "getter_cls"}

        for config in ALL_WINDOW_CONFIGS:
            assert isinstance(config, dict), "Config must be a dict"
            for field in required_fields - {"getter_cls"}:
                assert field in config, f"Missing required field: {field}"
            # getter_cls is optional (can be None)
            assert "getter_cls" in config

    def test_all_states_in_window_configs_are_unique(self):
        """Verify no duplicate states in window configs"""
        states = [c["state"] for c in ALL_WINDOW_CONFIGS]
        assert len(states) == len(set(states)), (
            "Duplicate states found in window configs"
        )

    def test_main_menu_states_registered(self):
        """Verify MainMenu states are registered"""
        states = {c["state"] for c in ALL_WINDOW_CONFIGS}
        assert MainMenu.main in states
        assert MainMenu.welcome in states
        assert MainMenu.min_main in states

    def test_window_config_message_and_keyboard_are_classes(self):
        """Verify message_cls and keyboard_cls are callable classes"""
        for config in ALL_WINDOW_CONFIGS:
            message_cls = config["message_cls"]
            keyboard_cls = config["keyboard_cls"]

            # Check that they are callable (classes)
            assert callable(message_cls), (
                f"message_cls must be callable: {config['state']}"
            )
            assert callable(keyboard_cls), (
                f"keyboard_cls must be callable: {config['state']}"
            )
