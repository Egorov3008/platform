"""
Tests for UserDataGetter using BackendAPIClient.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.backend_client import BackendAPIClient
from api.schemas import KeyDTO
from dialogs.windows.getters.profile.main import UserDataGetter


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def mock_checker_link():
    return AsyncMock()


@pytest.fixture
def mock_checked_user():
    return MagicMock()


@pytest.fixture
def sample_user():
    # BackendAPIClient.get_user() returns a plain dict (== UserResponse JSON).
    # Tests must mirror production reality — the getter now wraps it via
    # User.from_backend(), so this dict shape is what the code expects.
    return {
        "tg_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "balance": 0.0,
        "trial": 0,
        "server_id": 1,
        "is_admin": False,
        "is_blocked": False,
        "created_at": None,
    }


@pytest.fixture
def sample_keys():
    return [
        KeyDTO(
            email="test@example.com",
            tg_id=123456789,
            expiry_time=9999999999000,
            key="key_data",
            inbound_id=12,
            tariff_id=1,
            client_id="abc-123",
            name_tariff="Test",
        )
    ]


class TestUserDataGetterBasic:

    @pytest.mark.asyncio
    async def test_get_data_user_found_with_keys(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user, sample_keys,
    ):
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["username"] == "testuser"
        assert result["count_key"] == 1

    @pytest.mark.asyncio
    async def test_get_data_user_not_found(
        self, mock_backend, mock_checker_link, mock_checked_user, mock_dialog_manager
    ):
        mock_backend.get_user = AsyncMock(return_value=None)
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert "ID123456789" in result["username"]
        assert result["count_key"] == 0

    @pytest.mark.asyncio
    async def test_get_data_admin_user(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user, sample_keys,
    ):
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        mock_checked_user.check.return_value = True
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_get_data_trial_used(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user,
    ):
        sample_user["trial"] = 1
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["trial"] is False  # trial != 0

    @pytest.mark.asyncio
    async def test_get_data_no_keys(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user,
    ):
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["count_key"] == 0
        assert result["check_key"] is False


class TestUserDataGetterGiftLink:

    @pytest.mark.asyncio
    async def test_get_data_with_gift_link(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user,
    ):
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = True

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["check_usage_link"] is True
        mock_checker_link.check.assert_called_once_with(123456789)


class TestUserDataGetterIntegration:

    @pytest.mark.asyncio
    async def test_get_data_calls_backend_with_tg_id(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user, sample_keys,
    ):
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        await getter.get_data(mock_dialog_manager)

        mock_backend.get_user.assert_called_once_with(123456789)
        mock_backend.get_user_keys.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_get_data_full_profile(
        self, mock_backend, mock_checker_link, mock_checked_user,
        mock_dialog_manager, sample_user, sample_keys,
    ):
        sample_user["trial"] = 0
        mock_backend.get_user = AsyncMock(return_value=sample_user)
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        mock_checked_user.check.return_value = True
        mock_checker_link.check.return_value = True

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        for field in ["username", "count_key", "trial", "is_admin", "check_key", "check_usage_link"]:
            assert field in result

        assert result["username"] == "testuser"
        assert result["count_key"] == 1
        assert result["trial"] is True
        assert result["is_admin"] is True
        assert result["check_key"] is True
        assert result["check_usage_link"] is True

    @pytest.mark.asyncio
    async def test_error_fallback(
        self, mock_backend, mock_checker_link, mock_checked_user, mock_dialog_manager
    ):
        mock_backend.get_user = AsyncMock(side_effect=Exception("network error"))
        mock_backend.get_user_keys = AsyncMock(return_value=[])

        getter = UserDataGetter(mock_backend, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["count_key"] == 0
        assert result["check_key"] is False
