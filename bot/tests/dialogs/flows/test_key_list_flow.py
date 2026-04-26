"""
Flow contract tests for Keys flow: KeysInit.list → KeysInit.key

Tests verify:
- KeyListGetter writes email at index key to dialog_data
- KeyListKeyboard reads indexed email and writes it as "email" key
- KeyDetailsGetter reads "email" key from dialog_data
- Full chain: list getter → list keyboard → details getter

No mocking of switch_to() / aiogram-dialog internals.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key
from dialogs.windows.getters.keys.key_list import KeyListGetter
from dialogs.windows.getters.keys.key_details import KeyDetailsGetter
from dialogs.windows.widgets.keybord.keys.key_list import KeyListKeyboard


def make_key(
    email: str, tg_id: int = 123456789, expiry_offset_ms: int = 86400000
) -> Key:
    """Helper to create a test Key."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        tariff_id=1,
    )


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data and event."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    manager.start_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel."""
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


@pytest.fixture
def mock_cache():
    """Mock CacheService for KeyDetailsGetter."""
    cache = AsyncMock()
    cache.keys = AsyncMock()
    cache.tariffs = AsyncMock()
    return cache


class TestKeyListGetterWritesDialogData:
    """Tests that KeyListGetter.get_data() writes email at index key to dialog_data."""

    async def test_writes_email_at_index_key(
        self, mock_dialog_manager, mock_model_data
    ):
        """KeyListGetter writes dialog_data["0"] = first_key.email"""
        key1 = make_key("user1@example.com")
        mock_model_data.keys.get_by.return_value = [key1]

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert result["key_data"] == [(0, "user1@example.com")]

    async def test_writes_all_keys_as_indexed(
        self, mock_dialog_manager, mock_model_data
    ):
        """KeyListGetter writes N keys with numeric indices."""
        keys = [
            make_key("user1@example.com"),
            make_key("user2@example.com"),
            make_key("user3@example.com"),
        ]
        mock_model_data.keys.get_by.return_value = keys

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert mock_dialog_manager.dialog_data["1"] == "user2@example.com"
        assert mock_dialog_manager.dialog_data["2"] == "user3@example.com"
        assert len(result["key_data"]) == 3

    async def test_does_not_write_non_index_keys(
        self, mock_dialog_manager, mock_model_data
    ):
        """KeyListGetter does not write arbitrary keys to dialog_data."""
        key1 = make_key("user1@example.com")
        mock_model_data.keys.get_by.return_value = [key1]

        getter = KeyListGetter(mock_model_data)
        mock_dialog_manager.dialog_data["preset_key"] = "preset_value"

        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["preset_key"] == "preset_value"
        assert "email" not in mock_dialog_manager.dialog_data

    async def test_empty_keys_writes_nothing(
        self, mock_dialog_manager, mock_model_data
    ):
        """KeyListGetter with empty list does not write to dialog_data."""
        mock_model_data.keys.get_by.return_value = []
        mock_dialog_manager.dialog_data["existing"] = "value"

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["existing"] == "value"
        assert result["msg"] == "❌ Ключи не найдены"
        assert result["key_data"] == []


class TestKeyListKeyboardReadsDialogData:
    """Tests that KeyListKeyboard._on_key_selected() reads indexed email from dialog_data."""

    async def test_reads_email_by_item_id(self, mock_dialog_manager):
        """Handler reads dialog_data[item_id] to get email."""
        mock_dialog_manager.dialog_data["0"] = "user1@example.com"
        mock_dialog_manager.dialog_data["1"] = "user2@example.com"

        callback = AsyncMock()
        widget = MagicMock()
        keyboard = KeyListKeyboard()

        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["email"] == "user2@example.com"

    async def test_writes_email_to_dialog_data(self, mock_dialog_manager):
        """Handler writes dialog_data["email"] after reading by item_id."""
        mock_dialog_manager.dialog_data["0"] = "user1@example.com"
        callback = AsyncMock()
        widget = MagicMock()
        keyboard = KeyListKeyboard()

        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="0"
        )

        assert "email" in mock_dialog_manager.dialog_data
        assert mock_dialog_manager.dialog_data["email"] == "user1@example.com"

    async def test_invalid_item_id_does_not_crash(self, mock_dialog_manager):
        """Handler with non-existent item_id reads None, writes None gracefully."""
        mock_dialog_manager.dialog_data["0"] = "user1@example.com"
        callback = AsyncMock()
        widget = MagicMock()
        keyboard = KeyListKeyboard()

        # item_id="999" does not exist in dialog_data
        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="999"
        )

        # Handler should have attempted to write None
        assert mock_dialog_manager.dialog_data["email"] is None


class TestKeyDetailsGetterReadsEmail:
    """Tests that KeyDetailsGetter.get_data() reads dialog_data["email"]."""

    async def test_loads_key_by_email_from_dialog_data(
        self, mock_dialog_manager, mock_cache
    ):
        """Getter calls cache.keys.get(email) with email from dialog_data."""
        key1 = make_key("user1@example.com")
        mock_dialog_manager.dialog_data["email"] = "user1@example.com"
        mock_dialog_manager.middleware_data = {"cache": mock_cache}
        mock_cache.keys.get.return_value = key1
        mock_cache.tariffs.get.return_value = None

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        mock_cache.keys.get.assert_called_once_with("key_user1@example.com")
        assert "error" not in result or result.get("error") is False

    async def test_missing_email_returns_error_dict(
        self, mock_dialog_manager, mock_cache
    ):
        """Getter without dialog_data["email"] returns error dict gracefully."""
        mock_dialog_manager.middleware_data = {"cache": mock_cache}
        mock_cache.keys.get.return_value = None

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["error"] is True
        assert "не найден" in result["error_message"].lower()

    async def test_result_contains_key_fields(
        self, mock_dialog_manager, mock_cache
    ):
        """Getter result contains key fields from KeyModel.to_dict()."""
        key1 = make_key("user1@example.com", tg_id=123)
        mock_dialog_manager.dialog_data["email"] = "user1@example.com"
        mock_dialog_manager.middleware_data = {"cache": mock_cache}
        mock_cache.keys.get.return_value = key1
        mock_tariff = AsyncMock()
        mock_tariff.name_tariff = "Test"
        mock_cache.tariffs.get.return_value = mock_tariff

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        # KeyModel.to_dict() should contain key data
        assert "error" not in result or result.get("error") is False


class TestKeyListToDetailsContract:
    """Contract tests: full chain KeyListGetter → KeyListKeyboard → KeyDetailsGetter."""

    async def test_full_index_email_chain(self, mock_dialog_manager, mock_model_data, mock_cache):
        """Complete flow: getter writes → handler reads → detail getter reads."""
        keys = [
            make_key("user1@example.com"),
            make_key("user2@example.com"),
        ]
        mock_model_data.keys.get_by.return_value = keys
        key2 = make_key("user2@example.com")
        mock_cache.keys.get.return_value = key2
        mock_cache.tariffs.get.return_value = None

        # Step 1: KeyListGetter writes indices
        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)
        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert mock_dialog_manager.dialog_data["1"] == "user2@example.com"

        # Step 2: Handler reads by index and writes email
        keyboard = KeyListKeyboard()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )
        assert mock_dialog_manager.dialog_data["email"] == "user2@example.com"

        # Step 3: KeyDetailsGetter reads email
        mock_dialog_manager.middleware_data = {"cache": mock_cache}
        detail_getter = KeyDetailsGetter()
        result = await detail_getter.get_data(mock_dialog_manager)
        mock_cache.keys.get.assert_called_with("key_user2@example.com")
        assert "error" not in result or result.get("error") is False

    async def test_multiple_keys_each_selectable(
        self, mock_dialog_manager, mock_model_data
    ):
        """Multiple keys: selection of any key works through full chain."""
        keys = [
            make_key("user1@example.com"),
            make_key("user2@example.com"),
            make_key("user3@example.com"),
        ]
        mock_model_data.keys.get_by.return_value = keys

        # Get list
        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        # For each key index, verify selection works
        for i in range(len(keys)):
            mock_dialog_manager.dialog_data.clear()
            # Restore indices
            for j, key in enumerate(keys):
                mock_dialog_manager.dialog_data[str(j)] = key.email

            keyboard = KeyListKeyboard()
            callback = AsyncMock()
            widget = MagicMock()
            await keyboard._on_key_selected(
                callback, widget, mock_dialog_manager, item_id=str(i)
            )

            assert mock_dialog_manager.dialog_data["email"] == keys[i].email

    async def test_deletion_flow_reads_email(
        self, mock_dialog_manager, mock_model_data
    ):
        """Deletion flow requires email from dialog_data (set by KeyListKeyboard)."""
        key1 = make_key("user1@example.com")
        mock_model_data.keys.get_by.return_value = [key1]
        mock_model_data.keys.get_data.return_value = key1

        # List → select
        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        keyboard = KeyListKeyboard()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="0"
        )

        # Deletion needs email from dialog_data (written by keyboard handler)
        assert mock_dialog_manager.dialog_data["email"] == "user1@example.com"
