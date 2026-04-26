"""
Tests for AdminUserProfileGetter.

AdminUserProfileGetter.get_data():
- Reads tg_id from dialog_data first, falls back to start_data
- Fetches user via users.get_data(tg_id)
- Fetches all keys, filters by tg_id
- Formats profile message with trial status
- Handles missing tg_id and missing user gracefully
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from models import User, Key
from dialogs.windows.getters.admin.user_profile import AdminUserProfileGetter


def make_user(
    tg_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    trial: int = 0,
) -> User:
    return User(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        trial=trial,
        created_at=datetime.now(),
        server_id=1,
    )


def make_key(email: str, tg_id: int) -> Key:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + 10 * 24 * 3600 * 1000,
    )


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


# ---------------------------------------------------------------------------
# tg_id resolution
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterTgIdResolution:
    """tg_id must come from dialog_data first, then start_data."""

    async def test_tg_id_from_dialog_data(self, mock_model_data, mock_dialog_manager):
        """tg_id from dialog_data['tg_id'] is used when present."""
        user = make_user(111, username="alice")
        mock_dialog_manager.dialog_data["tg_id"] = 111
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "111" in result["msg"]
        mock_model_data.users.get_data.assert_called_once_with(111)

    async def test_tg_id_fallback_to_start_data(
        self, mock_model_data, mock_dialog_manager
    ):
        """When dialog_data has no tg_id, start_data is checked."""
        user = make_user(222, username="bob")
        mock_dialog_manager.dialog_data = {}  # no tg_id
        mock_dialog_manager.start_data = {"tg_id": 222}
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "222" in result["msg"]

    async def test_no_tg_id_returns_error(self, mock_model_data, mock_dialog_manager):
        """When tg_id is absent from both dialog_data and start_data, return error."""
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {}

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "❌" in result["msg"]
        assert result["keys"] == []

    async def test_dialog_data_tg_id_takes_priority_over_start_data(
        self, mock_model_data, mock_dialog_manager
    ):
        """dialog_data tg_id must be used even when start_data also has tg_id."""
        user = make_user(999, username="priority_user")
        mock_dialog_manager.dialog_data["tg_id"] = 999
        mock_dialog_manager.start_data = {"tg_id": 000}  # must not be used
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        mock_model_data.users.get_data.assert_called_once_with(999)


# ---------------------------------------------------------------------------
# User not found
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterUserNotFound:
    async def test_user_not_found_returns_error_msg(
        self, mock_model_data, mock_dialog_manager
    ):
        """When user does not exist in cache, return error msg with tg_id."""
        mock_dialog_manager.dialog_data["tg_id"] = 404
        mock_model_data.users.get_data.return_value = None

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "404" in result["msg"]
        assert "❌" in result["msg"]
        assert result["keys"] == []


# ---------------------------------------------------------------------------
# Profile message formatting
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterMessageFormat:
    async def test_username_appears_in_profile_msg(
        self, mock_model_data, mock_dialog_manager
    ):
        """Profile msg must include username."""
        user = make_user(123, username="john_doe")
        mock_dialog_manager.dialog_data["tg_id"] = 123
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "john_doe" in result["msg"]

    async def test_first_name_used_when_username_absent(
        self, mock_model_data, mock_dialog_manager
    ):
        """When username is None, first_name is shown instead."""
        user = make_user(789, username=None, first_name="Ivan")
        mock_dialog_manager.dialog_data["tg_id"] = 789
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "Ivan" in result["msg"]

    async def test_trial_used_shows_red_status(
        self, mock_model_data, mock_dialog_manager
    ):
        """User with trial=0 (used) must show red status marker."""
        user = make_user(111, username="tester", trial=0)
        mock_dialog_manager.dialog_data["tg_id"] = 111
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "🔴" in result["msg"]

    async def test_trial_available_shows_green_status(
        self, mock_model_data, mock_dialog_manager
    ):
        """User with trial > 0 (available) must show green status marker."""
        user = make_user(222, username="newuser", trial=1)
        mock_dialog_manager.dialog_data["tg_id"] = 222
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "🟢" in result["msg"]


# ---------------------------------------------------------------------------
# Key filtering
# ---------------------------------------------------------------------------


class TestAdminUserProfileGetterKeyFiltering:
    async def test_only_user_keys_returned(self, mock_model_data, mock_dialog_manager):
        """Only keys belonging to the requested tg_id must be in result['keys']."""
        target_tg_id = 555
        user = make_user(target_tg_id, username="target")
        mock_dialog_manager.dialog_data["tg_id"] = target_tg_id

        user_key = make_key("user@vpn.com", target_tg_id)
        other_key = make_key("other@vpn.com", 999)
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = [user_key, other_key]

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["keys"]) == 1
        assert result["keys"][0].tg_id == target_tg_id

    async def test_key_count_in_message(self, mock_model_data, mock_dialog_manager):
        """The number of user keys must appear in the profile message."""
        tg_id = 333
        user = make_user(tg_id, username="multikey")
        mock_dialog_manager.dialog_data["tg_id"] = tg_id

        keys = [make_key(f"k{i}@b.com", tg_id) for i in range(3)]
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "3" in result["msg"]

    async def test_result_contains_url_user(self, mock_model_data, mock_dialog_manager):
        """Result dict must include url_user with tg_id for deep link."""
        tg_id = 77777
        user = make_user(tg_id, username="link_user")
        mock_dialog_manager.dialog_data["tg_id"] = tg_id
        mock_model_data.users.get_data.return_value = user
        mock_model_data.keys.get_all.return_value = []

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "url_user" in result
        assert str(tg_id) in result["url_user"]

    async def test_exception_returns_error_dict(
        self, mock_model_data, mock_dialog_manager
    ):
        """When users.get_data() raises, result must contain error string."""
        mock_dialog_manager.dialog_data["tg_id"] = 1
        mock_model_data.users.get_data.side_effect = RuntimeError("DB error")

        getter = AdminUserProfileGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "❌" in result["msg"]
        assert result["keys"] == []
