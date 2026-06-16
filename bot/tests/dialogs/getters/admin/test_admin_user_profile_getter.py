"""
Tests for AdminUserProfileGetter.

AdminUserProfileGetter.get_data():
- Reads tg_id from dialog_data first, falls back to start_data
- Fetches user via backend.get_user(tg_id)
- Fetches user keys via backend.get_user_keys(tg_id)
- Formats profile message with trial status
- Handles missing tg_id and missing user gracefully
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from models import Key
from dialogs.windows.getters.admin.user_profile import AdminUserProfileGetter


def make_user_dict(
    tg_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    trial: int = 0,
) -> dict:
    return {
        "tg_id": tg_id,
        "username": username,
        "first_name": first_name,
        "trial": trial,
        "created_at": datetime.now().isoformat(),
        "server_id": 1,
    }


def make_key_dict(email: str, tg_id: int) -> dict:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "tg_id": tg_id,
        "client_id": "c1",
        "email": email,
        "expiry_time": now_ms + 10 * 24 * 3600 * 1000,
        "key": "k",
        "inbound_id": 1,
    }


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_backend():
    backend = AsyncMock()
    backend.get_user = AsyncMock(return_value=None)
    backend.get_user_keys = AsyncMock(return_value=[])
    return backend


# ---------------------------------------------------------------------------
# tg_id resolution
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterTgIdResolution:
    """tg_id must come from dialog_data first, then start_data."""

    async def test_tg_id_from_dialog_data(self, mock_backend, mock_dialog_manager):
        """tg_id from dialog_data['tg_id'] is used when present."""
        user = make_user_dict(111, username="alice")
        mock_dialog_manager.dialog_data["tg_id"] = 111
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "111" in result["msg"]
        mock_backend.get_user.assert_awaited_once_with(111)

    async def test_tg_id_fallback_to_start_data(
        self, mock_backend, mock_dialog_manager
    ):
        """When dialog_data has no tg_id, start_data is checked."""
        user = make_user_dict(222, username="bob")
        mock_dialog_manager.dialog_data = {}  # no tg_id
        mock_dialog_manager.start_data = {"tg_id": 222}
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "222" in result["msg"]

    async def test_no_tg_id_returns_error(self, mock_backend, mock_dialog_manager):
        """When tg_id is absent from both dialog_data and start_data, return error."""
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {}

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "❌" in result["msg"]
        assert result["keys"] == []

    async def test_dialog_data_tg_id_takes_priority_over_start_data(
        self, mock_backend, mock_dialog_manager
    ):
        """dialog_data tg_id must be used even when start_data also has tg_id."""
        user = make_user_dict(999, username="priority_user")
        mock_dialog_manager.dialog_data["tg_id"] = 999
        mock_dialog_manager.start_data = {"tg_id": 0}  # must not be used
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        mock_backend.get_user.assert_awaited_once_with(999)


# ---------------------------------------------------------------------------
# User not found
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterUserNotFound:
    async def test_user_not_found_returns_error_msg(
        self, mock_backend, mock_dialog_manager
    ):
        """When user does not exist, return error msg with tg_id."""
        mock_dialog_manager.dialog_data["tg_id"] = 404
        mock_backend.get_user.return_value = None

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "404" in result["msg"]
        assert "❌" in result["msg"]
        assert result["keys"] == []


# ---------------------------------------------------------------------------
# Profile message formatting
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterMessageFormat:
    async def test_username_appears_in_profile_msg(
        self, mock_backend, mock_dialog_manager
    ):
        """Profile msg must include username."""
        user = make_user_dict(123, username="john_doe")
        mock_dialog_manager.dialog_data["tg_id"] = 123
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "john_doe" in result["msg"]

    async def test_first_name_used_when_username_absent(
        self, mock_backend, mock_dialog_manager
    ):
        """When username is None, first_name is shown instead."""
        user = make_user_dict(789, username=None, first_name="Ivan")
        mock_dialog_manager.dialog_data["tg_id"] = 789
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Ivan" in result["msg"]

    async def test_trial_used_shows_red_status(
        self, mock_backend, mock_dialog_manager
    ):
        """User with trial=0 (used) must show red status marker."""
        user = make_user_dict(111, username="tester", trial=0)
        mock_dialog_manager.dialog_data["tg_id"] = 111
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "🔴" in result["msg"]

    async def test_trial_available_shows_green_status(
        self, mock_backend, mock_dialog_manager
    ):
        """User with trial > 0 (available) must show green status marker."""
        user = make_user_dict(222, username="newuser", trial=1)
        mock_dialog_manager.dialog_data["tg_id"] = 222
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "🟢" in result["msg"]


# ---------------------------------------------------------------------------
# Key filtering (handled by backend.get_user_keys — already filtered by tg_id)
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterKeyFiltering:
    async def test_user_keys_returned(self, mock_backend, mock_dialog_manager):
        """Keys returned from backend.get_user_keys() are passed through."""
        target_tg_id = 555
        user = make_user_dict(target_tg_id, username="target")
        mock_dialog_manager.dialog_data["tg_id"] = target_tg_id

        user_key = make_key_dict("user@vpn.com", target_tg_id)
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = [user_key]

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["keys"]) == 1
        assert result["keys"][0]["email"] == "user@vpn.com"

    async def test_key_count_in_message(self, mock_backend, mock_dialog_manager):
        """The number of user keys must appear in the profile message."""
        tg_id = 333
        user = make_user_dict(tg_id, username="multikey")
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        keys = [make_key_dict(f"k{i}@b.com", tg_id) for i in range(3)]
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = keys

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "3" in result["msg"]

    async def test_result_contains_user_id(self, mock_backend, mock_dialog_manager):
        """Result dict must include user_id (used by widgets to build deep links)."""
        tg_id = 77777
        user = make_user_dict(tg_id, username="link_user")
        mock_dialog_manager.dialog_data["tg_id"] = tg_id
        mock_backend.get_user.return_value = user
        mock_backend.get_user_keys.return_value = []

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "user_id" in result
        assert result["user_id"] == tg_id

    async def test_exception_returns_error_dict(
        self, mock_backend, mock_dialog_manager
    ):
        """When backend.get_user() raises, result must contain error string."""
        mock_dialog_manager.dialog_data["tg_id"] = 1
        mock_backend.get_user.side_effect = RuntimeError("Backend error")

        getter = AdminUserProfileGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "❌" in result["msg"]
        assert result["keys"] == []
