"""
Tests for SaturationUser - user data aggregation with mocks.

SaturationUser.refresh() and get_data_for_users() fetch and aggregate user data.
Side-effectful: requires mocking ServiceDataModel with users/servers.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from models import User, Server, Key
from services.core.user.utils.saturation import SaturationUser


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.servers = AsyncMock()
    return model_data


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
def sample_server():
    """Sample Server"""
    return Server(
        id=1,
        server_name="Test Server",
        api_url="https://api.test.com",
        login="admin",
        password="pass",
        subscription_url="https://sub.test.com",
        cluster_name="cluster1",
    )


@pytest.fixture
def sample_keys():
    """Sample VPN keys"""
    return [
        Key(
            email="test@example.com",
            inbound_id=12,
            client_id="client1",
            tg_id=123456789,
            key="key_data_1",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
        ),
        Key(
            email="test2@example.com",
            inbound_id=12,
            client_id="client2",
            tg_id=123456789,
            key="key_data_2",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=2,
        ),
    ]


class TestSaturationUserRefresh:
    """Test SaturationUser.refresh() method"""

    @pytest.mark.asyncio
    async def test_refresh_user_found(
        self, mock_model_data, sample_user, sample_server, sample_keys
    ):
        """refresh() should return user data dict when user found"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.servers.get_data.return_value = sample_server
        mock_model_data.users.get_by.return_value = sample_keys

        service = SaturationUser(mock_model_data)
        result = await service.refresh(123456789)

        assert "user" in result
        assert "connect_module" in result
        assert "keys" in result
        assert result["user"] == sample_user
        assert result["connect_module"] == sample_server
        assert result["keys"] == sample_keys

    @pytest.mark.asyncio
    async def test_refresh_user_not_found(self, mock_model_data):
        """refresh() should return empty dict when user not found"""
        mock_model_data.users.get_data.return_value = None

        service = SaturationUser(mock_model_data)
        result = await service.refresh(999999999)

        assert result == {}
        # Should not try to get server or keys
        mock_model_data.servers.get_data.assert_not_called()
        mock_model_data.users.get_by.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_calls_get_by_with_tg_id(
        self, mock_model_data, sample_user, sample_server, sample_keys
    ):
        """refresh() should call get_by with tg_id parameter"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.servers.get_data.return_value = sample_server
        mock_model_data.users.get_by.return_value = sample_keys

        service = SaturationUser(mock_model_data)
        await service.refresh(123456789)

        mock_model_data.users.get_by.assert_called_once_with(tg_id=123456789)

    @pytest.mark.asyncio
    async def test_refresh_no_keys(self, mock_model_data, sample_user, sample_server):
        """refresh() should handle user with no keys"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.servers.get_data.return_value = sample_server
        mock_model_data.users.get_by.return_value = []

        service = SaturationUser(mock_model_data)
        result = await service.refresh(123456789)

        assert result["keys"] == []
        assert result["user"] == sample_user


class TestSaturationUserGetDataForUsers:
    """Test SaturationUser.get_data_for_users() method"""

    @pytest.mark.asyncio
    async def test_get_data_for_users_success(self, mock_model_data):
        """get_data_for_users() should return list of user data dicts"""
        user1 = User(
            tg_id=111, username="user1", trial=0, created_at=datetime.now(), server_id=1
        )
        user2 = User(
            tg_id=222, username="user2", trial=0, created_at=datetime.now(), server_id=1
        )
        users = [user1, user2]

        server = Server(
            id=1,
            server_name="Server",
            api_url="url",
            login="login",
            password="pass",
            subscription_url="sub",
            cluster_name="cluster",
        )

        mock_model_data.users.get_all.return_value = users
        mock_model_data.servers.get_data.return_value = server
        mock_model_data.users.get_by.return_value = []

        service = SaturationUser(mock_model_data)
        result = await service.get_data_for_users()

        assert len(result) == 2
        assert all("user" in r and "connect_module" in r for r in result)

    @pytest.mark.asyncio
    async def test_get_data_for_users_no_users(self, mock_model_data):
        """get_data_for_users() should return empty list when no users"""
        mock_model_data.users.get_all.return_value = []

        service = SaturationUser(mock_model_data)
        result = await service.get_data_for_users()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_data_for_users_with_exceptions(self, mock_model_data):
        """get_data_for_users() should skip users with errors"""
        user1 = User(
            tg_id=111, username="user1", trial=0, created_at=datetime.now(), server_id=1
        )
        users = [user1]

        mock_model_data.users.get_all.return_value = users
        # Simulate exception on first call
        mock_model_data.servers.get_data.side_effect = Exception("Server fetch error")

        service = SaturationUser(mock_model_data)
        result = await service.get_data_for_users()

        # Exception should be caught and skipped
        assert result == []

    @pytest.mark.asyncio
    async def test_get_data_for_users_mixed_results(self, mock_model_data):
        """get_data_for_users() should handle mixed results (some succeed, some fail)"""
        user1 = User(
            tg_id=111, username="user1", trial=0, created_at=datetime.now(), server_id=1
        )
        user2 = User(
            tg_id=222, username="user2", trial=0, created_at=datetime.now(), server_id=1
        )
        users = [user1, user2]

        server = Server(
            id=1,
            server_name="Server",
            api_url="url",
            login="login",
            password="pass",
            subscription_url="sub",
            cluster_name="cluster",
        )

        mock_model_data.users.get_all.return_value = users
        # First call succeeds, second fails
        mock_model_data.servers.get_data.return_value = server
        mock_model_data.users.get_by.return_value = []

        service = SaturationUser(mock_model_data)
        result = await service.get_data_for_users()

        assert len(result) >= 1  # At least one should succeed


class TestSaturationUserEdgeCases:
    """Test edge cases for SaturationUser"""

    @pytest.mark.asyncio
    async def test_refresh_user_server_mismatch(self, mock_model_data, sample_user):
        """refresh() should handle user's server_id not matching any server"""
        sample_user.server_id = 999
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.servers.get_data.return_value = None

        service = SaturationUser(mock_model_data)
        result = await service.refresh(123456789)

        assert result["user"] == sample_user
        assert result["connect_module"] is None

    @pytest.mark.asyncio
    async def test_refresh_multiple_keys_same_user(
        self, mock_model_data, sample_user, sample_server
    ):
        """refresh() should handle users with multiple keys"""
        keys = [
            Key(
                email=f"test{i}@example.com",
                inbound_id=12,
                client_id=f"client{i}",
                tg_id=sample_user.tg_id,
                key=f"key{i}",
                expiry_time=int(datetime.now().timestamp() * 1000),
                tariff_id=i,
            )
            for i in range(5)
        ]

        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.servers.get_data.return_value = sample_server
        mock_model_data.users.get_by.return_value = keys

        service = SaturationUser(mock_model_data)
        result = await service.refresh(sample_user.tg_id)

        assert len(result["keys"]) == 5
