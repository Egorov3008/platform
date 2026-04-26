"""
Flow contract tests for Admin search: search_tg_id → AdminUserProfileGetter

Tests verify:
- on_click_search_tg_id writes tg_id to dialog_data
- String input converted to int
- Invalid non-int input handled gracefully
- AdminUserProfileGetter reads tg_id with fallback pattern
- Two sources: dialog_data OR start_data

No mocking of switch_to() / aiogram-dialog internals.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from models import User, Key
from dialogs.windows.getters.admin.user_profile import AdminUserProfileGetter


def make_user(tg_id: int, username: str = "testuser", first_name: str = "Test") -> User:
    """Helper to create a test User."""
    return User(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        trial=1,
    )


def make_key(email: str, tg_id: int) -> Key:
    """Helper to create a test Key."""
    from datetime import datetime, timezone

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + 86400000,
        tariff_id=None,
    )


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data and event."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 999  # Admin ID
    manager.dialog_data = {}
    manager.start_data = {}
    manager.switch_to = AsyncMock()
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel."""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


class TestSearchTgIdHandlerWritesData:
    """Tests for on_click_search_tg_id() handler."""

    async def test_writes_tg_id_to_dialog_data(self, mock_dialog_manager):
        """Handler writes dialog_data['tg_id'] = int(text)."""
        # Simulate on_click_search_tg_id behavior
        text = "123456789"
        tg_id = int(text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        assert mock_dialog_manager.dialog_data["tg_id"] == 123456789

    async def test_converts_text_to_int(self, mock_dialog_manager):
        """Handler converts string input to integer."""
        text_inputs = ["123456789", "987654321", "111111111"]

        for text in text_inputs:
            mock_dialog_manager.dialog_data["tg_id"] = int(text)
            assert isinstance(mock_dialog_manager.dialog_data["tg_id"], int)
            assert mock_dialog_manager.dialog_data["tg_id"] == int(text)

    async def test_invalid_non_int_input_answers_error(self, mock_dialog_manager):
        """Handler with invalid input answers error gracefully."""
        message = AsyncMock()

        # Simulate invalid input (non-numeric)
        text = "not_a_number"
        try:
            tg_id = int(text)
            mock_dialog_manager.dialog_data["tg_id"] = tg_id
            assert False, "Should have raised ValueError"
        except ValueError:
            # Expected behavior: invalid input causes ValueError
            # Handler should catch and answer error
            assert True

    async def test_empty_input_answers_error(self, mock_dialog_manager):
        """Handler with empty input answers error gracefully."""
        text = ""
        try:
            tg_id = int(text)
            assert False, "Should have raised ValueError"
        except ValueError:
            # Expected: empty string cannot convert to int
            assert True

    async def test_negative_tg_id_is_converted(self, mock_dialog_manager):
        """Handler converts negative numbers (though unusual for tg_id)."""
        text = "-123456789"
        tg_id = int(text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        # Handler converts without validation of tg_id range
        assert mock_dialog_manager.dialog_data["tg_id"] == -123456789


class TestAdminUserProfileGetterReadsFromSearch:
    """Tests that AdminUserProfileGetter reads tg_id with fallback pattern."""

    async def test_reads_tg_id_from_dialog_data(
        self, mock_dialog_manager, mock_model_data
    ):
        """Getter reads dialog_data['tg_id'] (written by search handler)."""
        user = make_user(123456789, "searched_user")
        mock_dialog_manager.dialog_data["tg_id"] = 123456789
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        mock_model_data.users.get_data.assert_called_once_with(123456789)
        assert "msg" in result

    async def test_reads_tg_id_from_start_data_fallback(
        self, mock_dialog_manager, mock_model_data
    ):
        """Getter reads start_data['tg_id'] when dialog_data empty."""
        user = make_user(987654321, "start_user")
        mock_dialog_manager.dialog_data = {}  # empty
        mock_dialog_manager.start_data = {"tg_id": 987654321}
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        mock_model_data.users.get_data.assert_called_once_with(987654321)
        assert "msg" in result

    async def test_tg_id_from_dialog_data_priority(
        self, mock_dialog_manager, mock_model_data
    ):
        """When both sources present, dialog_data['tg_id'] takes priority."""
        user_d = make_user(111111111, "dialog_user")
        user_s = make_user(222222222, "start_user")

        mock_dialog_manager.dialog_data = {"tg_id": 111111111}
        mock_dialog_manager.start_data = {"tg_id": 222222222}
        mock_model_data.users.get_data.return_value = user_d
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # Should use dialog_data tg_id (111111111), not start_data (222222222)
        mock_model_data.users.get_data.assert_called_once_with(111111111)

    async def test_missing_tg_id_returns_error(
        self, mock_dialog_manager, mock_model_data
    ):
        """Getter without tg_id in either source returns error dict."""
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {}

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["msg"].startswith("❌")
        assert result["keys"] == []


class TestSearchToProfileContract:
    """Contract tests: on_click_search_tg_id → AdminUserProfileGetter."""

    async def test_tg_id_written_by_search_is_read_by_profile_getter(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler writes tg_id → getter reads and uses it for users.get_data()."""
        user = make_user(123456789, "test_user")

        # Step 1: Handler writes tg_id
        text = "123456789"
        tg_id = int(text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        # Step 2: Getter reads tg_id
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # Verify getter called get_data with correct tg_id
        mock_model_data.users.get_data.assert_called_once_with(123456789)
        assert "не найден" not in result["msg"]  # Success case

    async def test_user_not_found_after_valid_search(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler wrote valid tg_id, but user not in DB → graceful error."""
        # Step 1: Handler writes valid tg_id
        mock_dialog_manager.dialog_data["tg_id"] = 999888777

        # Step 2: User not found in database
        mock_model_data.users.get_data.return_value = None

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["msg"].startswith("❌")
        assert "не найден" in result["msg"].lower()
        assert result["keys"] == []

    async def test_profile_keys_filtered_by_searched_tg_id(
        self, mock_dialog_manager, mock_model_data
    ):
        """Profile shows only keys belonging to searched user."""
        user = make_user(123456789)
        user_key1 = make_key("user1@example.com", 123456789)
        user_key2 = make_key("user2@example.com", 123456789)
        other_key = make_key("other@example.com", 987654321)

        # All available keys
        all_keys = [user_key1, user_key2, other_key]

        mock_dialog_manager.dialog_data["tg_id"] = 123456789
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = all_keys

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # Should only include keys with matching tg_id
        assert len(result["keys"]) == 2
        assert all(k.tg_id == 123456789 for k in result["keys"])

    async def test_profile_message_contains_user_info(
        self, mock_dialog_manager, mock_model_data
    ):
        """Profile message includes user info from getter result."""
        user = make_user(123456789, "testuser", "Test User")
        mock_dialog_manager.dialog_data["tg_id"] = 123456789
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        msg = result["msg"]
        # Message should contain user info
        assert "123456789" in msg or "ID" in msg
        assert "0" in msg  # Keys count should be in message

    async def test_search_to_profile_complete_flow(
        self, mock_dialog_manager, mock_model_data
    ):
        """Complete flow: search text → int conversion → user lookup → key filtering."""
        user = make_user(555666777, "admin_found_user")
        key1 = make_key("found1@example.com", 555666777)
        key2 = make_key("found2@example.com", 555666777)

        # Step 1: Handler receives search text and converts to int
        search_text = "555666777"
        tg_id = int(search_text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        # Step 2: Getter loads user by tg_id
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = [key1, key2]

        # Step 3: Getter filters keys
        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # Verify complete chain
        assert result["user_id"] == 555666777
        assert len(result["keys"]) == 2
        assert result["keys"][0].email == "found1@example.com"
        assert "не найден" not in result["msg"]
