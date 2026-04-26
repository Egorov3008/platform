"""
Tests for UserDataGetter - profile data for dialog display.

UserDataGetter.get_data() gathers user data for the main profile dialog.
Side-effectful: requires mocking ServiceDataModel, CheckerGiftLink, CheckedUser, DialogManager.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import User, Key
from dialogs.windows.getters.profile.main import UserDataGetter


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager for dialog testing"""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


@pytest.fixture
def mock_checker_link():
    """Mock CheckerGiftLink"""
    return AsyncMock()


@pytest.fixture
def mock_checked_user():
    """Mock CheckedUser"""
    return MagicMock()


@pytest.fixture
def sample_user():
    """Sample User"""
    return User(
        tg_id=123456789,
        username="testuser",
        trial=0,
        created_at=datetime.now(),
        server_id=1,
    )


@pytest.fixture
def sample_keys():
    """Sample Keys for user"""
    return [
        Key(
            email="test@example.com",
            inbound_id=12,
            client_id="client1",
            tg_id=123456789,
            key="key_data",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
        )
    ]


class TestUserDataGetterBasic:
    """Test UserDataGetter.get_data() with various user states"""

    @pytest.mark.asyncio
    async def test_get_data_user_found_with_keys(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
        sample_keys,
    ):
        """get_data() should return user data with keys"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = sample_keys
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert "username" in result
        assert "count_key" in result
        assert "trial" in result
        assert result["count_key"] == 1
        assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_data_user_not_found(
        self, mock_model_data, mock_checker_link, mock_checked_user, mock_dialog_manager
    ):
        """get_data() should handle user not found"""
        mock_model_data.users.get_data.return_value = None
        mock_model_data.keys.get_by.return_value = None
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert "username" in result
        assert result["count_key"] == 0
        assert "ID123456789" in result["username"]

    @pytest.mark.asyncio
    async def test_get_data_admin_user(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
        sample_keys,
    ):
        """get_data() should mark admin users"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = sample_keys
        mock_checked_user.check.return_value = True  # Admin!
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_get_data_user_in_trial(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
        sample_keys,
    ):
        """get_data() should detect trial users"""
        sample_user.trial = 1
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = sample_keys
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["trial"] is False  # trial != 0

    @pytest.mark.asyncio
    async def test_get_data_no_keys(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
    ):
        """get_data() should handle user with no keys"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = None
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["count_key"] == 0
        assert result["check_key"] is False


class TestUserDataGetterMultipleKeys:
    """Test UserDataGetter with multiple keys"""

    @pytest.mark.asyncio
    async def test_get_data_single_key_not_list(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
    ):
        """get_data() should handle get_by returning single Key (not list)"""
        single_key = sample_user
        key = Key(
            email="single@example.com",
            inbound_id=12,
            client_id="client1",
            tg_id=123456789,
            key="key_data",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
        )
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = key  # Single key, not list!
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["count_key"] == 1

    @pytest.mark.asyncio
    async def test_get_data_multiple_keys(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
    ):
        """get_data() should handle multiple keys"""
        keys = [
            Key(
                email=f"key{i}@example.com",
                inbound_id=12,
                client_id=f"client{i}",
                tg_id=123456789,
                key=f"key_data{i}",
                expiry_time=int(datetime.now().timestamp() * 1000),
                tariff_id=1,
            )
            for i in range(3)
        ]
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = keys
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["count_key"] == 3


class TestUserDataGetterGiftLink:
    """Test UserDataGetter gift link checking"""

    @pytest.mark.asyncio
    async def test_get_data_with_gift_link(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
    ):
        """get_data() should check for gift links"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = None
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = True  # Has gift link!

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        assert result["check_usage_link"] is True
        mock_checker_link.check.assert_called_once_with(123456789)


class TestUserDataGetterIntegration:
    """Integration tests for UserDataGetter"""

    @pytest.mark.asyncio
    async def test_get_data_calls_all_services(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
        sample_keys,
    ):
        """get_data() should call all required services"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = sample_keys
        mock_checked_user.check.return_value = False
        mock_checker_link.check.return_value = False

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        await getter.get_data(mock_dialog_manager)

        mock_model_data.users.get_data.assert_called_once()
        mock_model_data.keys.get_by.assert_called_once()
        mock_checked_user.check.assert_called_once()
        mock_checker_link.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_full_user_profile(
        self,
        mock_model_data,
        mock_checker_link,
        mock_checked_user,
        mock_dialog_manager,
        sample_user,
        sample_keys,
    ):
        """get_data() should return complete user profile data"""
        sample_user.trial = 0
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.keys.get_by.return_value = sample_keys
        mock_checked_user.check.return_value = True
        mock_checker_link.check.return_value = True

        getter = UserDataGetter(mock_model_data, mock_checker_link, mock_checked_user)
        result = await getter.get_data(mock_dialog_manager)

        # Verify all required fields present
        required_fields = [
            "username",
            "count_key",
            "trial",
            "is_admin",
            "check_key",
            "check_usage_link",
        ]
        for field in required_fields:
            assert field in result

        # Verify values
        assert result["username"] == "testuser"
        assert result["count_key"] == 1
        assert result["trial"] is True  # No trial (trial == 0)
        assert result["is_admin"] is True
        assert result["check_key"] is True  # Has keys
        assert result["check_usage_link"] is True
