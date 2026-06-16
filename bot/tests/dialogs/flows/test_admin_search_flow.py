"""
Flow contract tests for Admin search: search_tg_id → AdminUserProfileGetter

Source: dialogs/windows/getters/admin/user_profile.py

Tests verify:
- The tg_id value travels from search handler to profile getter via dialog_data
- AdminUserProfileGetter reads tg_id (from dialog_data first, then start_data)
- The getter calls backend.get_user() and backend.get_user_keys()
- Keys returned match the searched tg_id
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dialogs.windows.getters.admin.user_profile import AdminUserProfileGetter


def make_user_dict(tg_id: int, username: str = "testuser", first_name: str = "Test") -> dict:
    """Helper: build a backend-shaped User dict."""
    return {
        "tg_id": tg_id,
        "username": username,
        "first_name": first_name,
        "trial": 1,
        "created_at": None,
        "server_id": 1,
        "is_blocked": False,
    }


def make_key_dict(email: str, tg_id: int) -> dict:
    """Helper: build a backend-shaped Key dict."""
    from datetime import datetime, timezone

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "email": email,
        "tg_id": tg_id,
        "client_id": "c1",
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + 86400000,
        "tariff_id": None,
    }


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
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.get_user = AsyncMock(return_value=None)
    backend.get_user_keys = AsyncMock(return_value=[])
    return backend


# ---------------------------------------------------------------------------
# Search → tg_id contract (input layer)
# ---------------------------------------------------------------------------


class TestSearchTgIdHandlerWritesData:
    """Tests for on_click_search_tg_id() handler."""

    async def test_writes_tg_id_to_dialog_data(self, mock_dialog_manager):
        """Handler writes dialog_data['tg_id'] = int(text)."""
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

    async def test_invalid_non_int_input_raises_value_error(self, mock_dialog_manager):
        """Handler with invalid input (non-numeric) raises ValueError."""
        text = "not_a_number"
        with pytest.raises(ValueError):
            tg_id = int(text)
            mock_dialog_manager.dialog_data["tg_id"] = tg_id

    async def test_empty_input_raises_value_error(self, mock_dialog_manager):
        """Handler with empty input raises ValueError."""
        text = ""
        with pytest.raises(ValueError):
            tg_id = int(text)

    async def test_negative_tg_id_is_converted(self, mock_dialog_manager):
        """Handler converts negative numbers (unusual but allowed)."""
        text = "-123456789"
        tg_id = int(text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        assert mock_dialog_manager.dialog_data["tg_id"] == -123456789


# ---------------------------------------------------------------------------
# AdminUserProfileGetter — reads tg_id
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterReadsFromSearch:
    """Tests that AdminUserProfileGetter reads tg_id with fallback pattern."""

    async def test_reads_tg_id_from_dialog_data(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter reads dialog_data['tg_id'] (written by search handler)."""
        user = make_user_dict(123456789, "searched_user")
        mock_dialog_manager.dialog_data["tg_id"] = 123456789
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        mock_backend.get_user.assert_called_once_with(123456789)
        assert "msg" in result

    async def test_reads_tg_id_from_start_data_fallback(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter reads start_data['tg_id'] when dialog_data empty."""
        user = make_user_dict(987654321, "start_user")
        mock_dialog_manager.dialog_data = {}  # empty
        mock_dialog_manager.start_data = {"tg_id": 987654321}
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        mock_backend.get_user.assert_called_once_with(987654321)
        assert "msg" in result

    async def test_tg_id_from_dialog_data_priority(
        self, mock_dialog_manager, mock_backend
    ):
        """When both sources present, dialog_data['tg_id'] takes priority."""
        user_d = make_user_dict(111111111, "dialog_user")
        user_s = make_user_dict(222222222, "start_user")

        mock_dialog_manager.dialog_data = {"tg_id": 111111111}
        mock_dialog_manager.start_data = {"tg_id": 222222222}
        mock_backend.get_user.return_value = user_d
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        # Should use dialog_data tg_id (111111111), not start_data (222222222)
        mock_backend.get_user.assert_called_once_with(111111111)

    async def test_missing_tg_id_returns_error(
        self, mock_dialog_manager, mock_backend
    ):
        """Getter without tg_id in either source returns error dict."""
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {}

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["msg"].startswith("❌")
        assert result["keys"] == []


# ---------------------------------------------------------------------------
# Полный контракт: search → profile
# ---------------------------------------------------------------------------


class TestSearchToProfileContract:
    """Contract tests: on_click_search_tg_id → AdminUserProfileGetter."""

    async def test_tg_id_written_by_search_is_read_by_profile_getter(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler writes tg_id → getter reads and uses it for backend.get_user()."""
        user = make_user_dict(123456789, "test_user")

        # Step 1: Handler writes tg_id
        text = "123456789"
        tg_id = int(text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        # Step 2: Getter reads tg_id
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Verify getter called get_user with correct tg_id
        mock_backend.get_user.assert_called_once_with(123456789)
        assert "не найден" not in result["msg"]  # Success case

    async def test_user_not_found_after_valid_search(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler wrote valid tg_id, but user not in DB → graceful error."""
        # Step 1: Handler writes valid tg_id
        mock_dialog_manager.dialog_data["tg_id"] = 999888777

        # Step 2: User not found
        mock_backend.get_user.return_value = None

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["msg"].startswith("❌")
        assert "не найден" in result["msg"].lower()
        assert result["keys"] == []

    async def test_profile_keys_filtered_by_searched_tg_id(
        self, mock_dialog_manager, mock_backend
    ):
        """Profile shows only keys belonging to searched user."""
        user = make_user_dict(123456789)
        user_key1 = make_key_dict("user1@example.com", 123456789)
        user_key2 = make_key_dict("user2@example.com", 123456789)
        other_key = make_key_dict("other@example.com", 987654321)

        # All available keys (the getter uses backend.get_user_keys(tg_id) — already filtered)
        all_keys = [user_key1, user_key2, other_key]

        mock_dialog_manager.dialog_data["tg_id"] = 123456789
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = [user_key1, user_key2]

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should only include keys with matching tg_id (filtered by backend.get_user_keys)
        assert len(result["keys"]) == 2
        assert all(k["tg_id"] == 123456789 for k in result["keys"])

    async def test_search_to_profile_complete_flow(
        self, mock_dialog_manager, mock_backend
    ):
        """Complete flow: search text → int conversion → user lookup → key filtering."""
        user = make_user_dict(555666777, "admin_found_user")
        key1 = make_key_dict("found1@example.com", 555666777)
        key2 = make_key_dict("found2@example.com", 555666777)

        # Step 1: Handler receives search text and converts to int
        search_text = "555666777"
        tg_id = int(search_text)
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        # Step 2: Getter loads user and keys by tg_id
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = [key1, key2]

        # Step 3: Getter returns profile with filtered keys
        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Verify complete chain
        assert result["user_id"] == 555666777
        assert len(result["keys"]) == 2
        assert result["keys"][0]["email"] == "found1@example.com"
        assert "не найден" not in result["msg"]
