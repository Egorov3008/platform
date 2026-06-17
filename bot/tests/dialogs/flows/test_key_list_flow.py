"""
Flow contract tests for Keys flow: KeysInit.list → KeysInit.key

Source: dialogs/windows/getters/keys/key_list.py
        dialogs/windows/getters/keys/key_details.py
        dialogs/windows/widgets/keybord/keys/key_list.py

Tests verify:
- KeyListGetter writes email at index key to dialog_data
- KeyListKeyboard reads indexed email and writes it as "email" key
- KeyDetailsGetter reads "email" key from dialog_data and fetches via backend
- Full chain: list getter → list keyboard → details getter
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.schemas import KeyDTO
from dialogs.windows.getters.keys.key_list import KeyListGetter
from dialogs.windows.getters.keys.key_details import KeyDetailsGetter
from dialogs.windows.widgets.keybord.keys.key_list import KeyListKeyboard


def make_key_dto(
    email: str, tg_id: int = 123456789, expiry_offset_ms: int = 86400000
) -> KeyDTO:
    """Build a KeyDTO (Pydantic) with expiry relative to now."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return KeyDTO(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        tariff_id=1,
    )


def make_key_data_dict(
    email: str, tg_id: int = 123456789, expiry_offset_ms: int = 86400000,
    **overrides,
) -> dict:
    """Build a backend-shaped dict for get_key_details() return value."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    data = {
        "email": email,
        "tg_id": tg_id,
        "client_id": "c1",
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "tariff_id": 1,
        "name_tariff": "Pro",
        "used_traffic": 0,
        "is_active": True,
        "days_left": 30,
        "hours_left": 0,
        "is_trial": False,
    }
    data.update(overrides)
    return data


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
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.get_user_keys = AsyncMock(return_value=[])
    backend.get_key_details = AsyncMock(return_value=None)
    return backend


# ---------------------------------------------------------------------------
# KeyListGetter — пишет в dialog_data
# ---------------------------------------------------------------------------


class TestKeyListGetterWritesDialogData:
    """Tests that KeyListGetter.get_data() writes email at index key to dialog_data."""

    async def test_writes_email_at_index_key(
        self, mock_dialog_manager, mock_backend
    ):
        """KeyListGetter writes dialog_data["0"] = first_key.email"""
        key1 = make_key_dto("user1@example.com")
        mock_backend.get_user_keys.return_value = [key1]

        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert result["key_data"] == [(0, "user1@example.com")]

    async def test_writes_all_keys_as_indexed(
        self, mock_dialog_manager, mock_backend
    ):
        """KeyListGetter writes N keys with numeric indices."""
        keys = [
            make_key_dto("user1@example.com"),
            make_key_dto("user2@example.com"),
            make_key_dto("user3@example.com"),
        ]
        mock_backend.get_user_keys.return_value = keys

        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert mock_dialog_manager.dialog_data["1"] == "user2@example.com"
        assert mock_dialog_manager.dialog_data["2"] == "user3@example.com"
        assert len(result["key_data"]) == 3

    async def test_does_not_write_non_index_keys(
        self, mock_dialog_manager, mock_backend
    ):
        """KeyListGetter does not overwrite arbitrary dialog_data keys."""
        key1 = make_key_dto("user1@example.com")
        mock_backend.get_user_keys.return_value = [key1]
        mock_dialog_manager.dialog_data["preset_key"] = "preset_value"

        getter = KeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        # Preset value is preserved
        assert mock_dialog_manager.dialog_data["preset_key"] == "preset_value"
        # Index 0 was written
        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"

    async def test_empty_keys_writes_nothing(
        self, mock_dialog_manager, mock_backend
    ):
        """KeyListGetter with empty list returns 'not found' message."""
        mock_backend.get_user_keys.return_value = []
        mock_dialog_manager.dialog_data["existing"] = "value"

        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["existing"] == "value"
        assert "❌" in result["msg"]
        assert result["key_data"] == []


# ---------------------------------------------------------------------------
# KeyListKeyboard — читает из dialog_data
# ---------------------------------------------------------------------------


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

    async def test_invalid_item_id_writes_none(self, mock_dialog_manager):
        """Handler with non-existent item_id writes None gracefully."""
        mock_dialog_manager.dialog_data["0"] = "user1@example.com"
        callback = AsyncMock()
        widget = MagicMock()
        keyboard = KeyListKeyboard()

        # item_id="999" does not exist in dialog_data
        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="999"
        )

        # Handler writes None for unknown id
        assert mock_dialog_manager.dialog_data["email"] is None


# ---------------------------------------------------------------------------
# KeyDetailsGetter — читает email
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterReadsEmail:
    """Tests that KeyDetailsGetter.get_data() reads dialog_data["email"]."""

    async def test_loads_key_by_email_from_dialog_data(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter calls backend.get_key_details(email) with email from dialog_data."""
        key_data = make_key_data_dict("user1@example.com")
        mock_dialog_manager.dialog_data["email"] = "user1@example.com"
        mock_backend.get_key_details.return_value = key_data

        getter = KeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        mock_backend.get_key_details.assert_called_once_with("user1@example.com")
        assert result.get("error") is False

    async def test_missing_email_returns_error_dict(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter without dialog_data["email"] returns error dict gracefully."""
        getter = KeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["error"] is True
        assert "не найден" in result["error_message"].lower()

    async def test_result_contains_key_fields(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter result contains formatted key fields."""
        key_data = make_key_data_dict(
            "user1@example.com", tg_id=123, used_traffic=5 * (1024 ** 3),
            name_tariff="Test", key="vpn-key-string",
        )
        mock_dialog_manager.dialog_data["email"] = "user1@example.com"
        mock_backend.get_key_details.return_value = key_data

        getter = KeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is False
        assert "tariff_name" in result
        assert "used_traffic" in result
        assert "status_emoji" in result


# ---------------------------------------------------------------------------
# Полный контракт: list → keyboard → details
# ---------------------------------------------------------------------------


class TestKeyListToDetailsContract:
    """Contract tests: full chain KeyListGetter → KeyListKeyboard → KeyDetailsGetter."""

    async def test_full_index_email_chain(
        self, mock_dialog_manager, mock_backend
    ):
        """Complete flow: getter writes → handler reads → detail getter reads."""
        keys = [
            make_key_dto("user1@example.com"),
            make_key_dto("user2@example.com"),
        ]
        mock_backend.get_user_keys.return_value = keys
        # get_key_details returns dict (per current source)
        key2 = make_key_data_dict("user2@example.com")
        mock_backend.get_key_details.return_value = key2

        # Step 1: KeyListGetter writes indices
        getter = KeyListGetter(mock_backend)
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
        detail_getter = KeyDetailsGetter(mock_backend)
        result = await detail_getter.get_data(mock_dialog_manager)
        mock_backend.get_key_details.assert_called_with("user2@example.com")
        assert result.get("error") is False

    async def test_multiple_keys_each_selectable(
        self, mock_dialog_manager, mock_backend
    ):
        """Multiple keys: selection of any key works through full chain."""
        keys = [
            make_key_dto("user1@example.com"),
            make_key_dto("user2@example.com"),
            make_key_dto("user3@example.com"),
        ]
        mock_backend.get_user_keys.return_value = keys

        # Get list
        getter = KeyListGetter(mock_backend)
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

    async def test_deletion_flow_reads_email(self, mock_dialog_manager, mock_backend):
        """Deletion flow requires email from dialog_data (set by KeyListKeyboard)."""
        key1 = make_key_dto("user1@example.com")
        mock_backend.get_user_keys.return_value = [key1]

        # List → select
        getter = KeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        keyboard = KeyListKeyboard()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_key_selected(
            callback, widget, mock_dialog_manager, item_id="0"
        )

        # Deletion needs email from dialog_data (written by keyboard handler)
        assert mock_dialog_manager.dialog_data["email"] == "user1@example.com"
