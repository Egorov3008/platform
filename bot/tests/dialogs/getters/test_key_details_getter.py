"""
Tests for KeyDetailsGetter - key detail view with status and traffic info.

KeyDetailsGetter.get_data() fetches key details and formats via KeyModel.
Side-effectful: requires mocking ServiceDataModel.keys.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from models import Key
from dialogs.windows.getters.keys.key_details import KeyDetailsGetter


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data and cache in middleware_data"""
    manager = AsyncMock()
    manager.dialog_data = {"email": "test@example.com"}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


@pytest.fixture
def mock_cache():
    """Mock CacheService for KeyDetailsGetter"""
    cache = AsyncMock()
    cache.keys = AsyncMock()
    return cache


@pytest.fixture
def active_key():
    """Active key (not expired)"""
    expiry_time = int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)
    return Key(
        email="test@example.com",
        inbound_id=12,
        client_id="client1",
        tg_id=123456789,
        key="vpn_key_data",
        expiry_time=expiry_time,
        tariff_id=1,
        name_tariff="Premium",
        used_traffic=1024**3,  # 1 GB
        total_gb=10 * (1024**3),  # 10 GB
    )


@pytest.fixture
def expired_key():
    """Expired key"""
    expiry_time = int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000)
    return Key(
        email="expired@example.com",
        inbound_id=12,
        client_id="client2",
        tg_id=123456789,
        key="expired_key",
        expiry_time=expiry_time,
        tariff_id=2,
        name_tariff="Basic",
    )


@pytest.fixture
def trial_key():
    """Trial key (tariff_id=10)"""
    expiry_time = int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000)
    return Key(
        email="trial@example.com",
        inbound_id=12,
        client_id="client3",
        tg_id=123456789,
        key="trial_key",
        expiry_time=expiry_time,
        tariff_id=10,  # Trial tariff
        name_tariff="Trial",
    )


class TestKeyDetailsGetterBasic:
    """Test KeyDetailsGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_key_found(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should return key details when found"""
        mock_cache.keys.get.return_value = active_key
        mock_cache.tariffs.get.return_value = None
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        mock_cache.keys.get.assert_called_once_with("key_test@example.com")
        assert result["error"] is False
        assert "keys" in result
        assert result["keys"] == "vpn_key_data"

    @pytest.mark.asyncio
    async def test_get_data_key_not_found(self, mock_model_data, mock_dialog_manager, mock_cache):
        """get_data() should return error when key not found"""
        mock_cache.keys.get.return_value = None
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["error"] is True
        assert result["error_message"] == "❌ Ключ не найден"

    @pytest.mark.asyncio
    async def test_get_data_calls_get_data_with_email(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should call get with email from dialog_data"""
        mock_cache.keys.get.return_value = active_key
        mock_cache.tariffs.get.return_value = None
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        await getter.get_data(mock_dialog_manager)

        mock_cache.keys.get.assert_called_once_with("key_test@example.com")


class TestKeyDetailsGetterStatus:
    """Test KeyDetailsGetter key status handling"""

    @pytest.mark.asyncio
    async def test_get_data_active_key_status(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should mark active keys correctly"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is True
        assert result["status_emoji"] == "🟢"
        assert result["status_text"] == "Активна"

    @pytest.mark.asyncio
    async def test_get_data_expired_key_status(
        self, mock_model_data, mock_dialog_manager, mock_cache, expired_key
    ):
        """get_data() should mark expired keys correctly"""
        mock_cache.keys.get.return_value = expired_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is False
        assert result["status_emoji"] == "🔴"
        assert result["status_text"] == "Истекла"

    @pytest.mark.asyncio
    async def test_get_data_expiring_soon_key_status(
        self, mock_model_data, mock_dialog_manager, mock_cache
    ):
        """get_data() should mark expiring-soon keys correctly"""
        expiry_time = int((datetime.utcnow() + timedelta(hours=12)).timestamp() * 1000)
        expiring_key = Key(
            email="expiring@example.com",
            inbound_id=12,
            client_id="client4",
            tg_id=123456789,
            key="expiring_key",
            expiry_time=expiry_time,
            tariff_id=2,
        )
        mock_cache.keys.get.return_value = expiring_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is True
        assert result["status_emoji"] == "🟡"
        assert result["status_text"] == "Заканчивается"


class TestKeyDetailsGetterTraffic:
    """Test KeyDetailsGetter traffic calculation"""

    @pytest.mark.asyncio
    async def test_get_data_traffic_info(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should calculate traffic usage correctly"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "used_traffic" in result
        assert "total_gb" in result
        assert "usage_percent" in result
        assert "progress_bar" in result
        # 1 GB out of 10 GB = 10%
        assert result["usage_percent"] == 10.0
        assert result["used_traffic"] == 1.0

    @pytest.mark.asyncio
    async def test_get_data_progress_bar(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should generate progress bar"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        progress_bar = result["progress_bar"]
        # 1 GB / 10 GB = 10% = 1 filled block out of 10
        assert "█" in progress_bar or "░" in progress_bar


class TestKeyDetailsGetterTariff:
    """Test KeyDetailsGetter tariff handling"""

    @pytest.mark.asyncio
    async def test_get_data_regular_tariff(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should mark non-trial tariffs"""
        mock_cache.keys.get.return_value = active_key
        mock_tariff = AsyncMock()
        mock_tariff.name_tariff = "Premium"
        mock_tariff.id = 1
        mock_cache.tariffs.get.return_value = mock_tariff
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_trial"] is False
        assert result["not_trial_tariff"] is True
        assert result["tariff_name"] == "Premium"

    @pytest.mark.asyncio
    async def test_get_data_trial_tariff(
        self, mock_model_data, mock_dialog_manager, mock_cache, trial_key
    ):
        """get_data() should mark trial tariffs (tariff_id=10)"""
        mock_cache.keys.get.return_value = trial_key
        mock_tariff = AsyncMock()
        mock_tariff.name_tariff = "Trial"
        mock_tariff.id = 10
        mock_cache.tariffs.get.return_value = mock_tariff
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["is_trial"] is True
        assert result["not_trial_tariff"] is False

    @pytest.mark.asyncio
    async def test_get_data_tariff_name_fallback(
        self, mock_model_data, mock_dialog_manager, mock_cache
    ):
        """get_data() should use default tariff name if not set"""
        expiry_time = int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)
        key_no_tariff = Key(
            email="notariff@example.com",
            inbound_id=12,
            client_id="client5",
            tg_id=123456789,
            key="key_no_tariff",
            expiry_time=expiry_time,
            tariff_id=1,
            name_tariff=None,
        )
        mock_cache.keys.get.return_value = key_no_tariff
        mock_cache.tariffs.get.return_value = None
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Не указан"


class TestKeyDetailsGetterExpiry:
    """Test KeyDetailsGetter expiry information"""

    @pytest.mark.asyncio
    async def test_get_data_expiry_date_format(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should format expiry date correctly"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "expiry_date" in result
        assert len(result["expiry_date"]) > 0

    @pytest.mark.asyncio
    async def test_get_data_days_left(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should calculate days_left correctly"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "days_left" in result
        assert result["days_left"] > 0

    @pytest.mark.asyncio
    async def test_get_data_time_left_message(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should generate time_left_message"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "time_left_message" in result
        assert len(result["time_left_message"]) > 0


class TestKeyDetailsGetterIntegration:
    """Integration tests for KeyDetailsGetter"""

    @pytest.mark.asyncio
    async def test_get_data_full_active_key_flow(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should handle complete active key flow"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        # Verify all required fields present
        required_fields = [
            "error",
            "keys",
            "tariff_name",
            "used_traffic",
            "total_gb",
            "progress_bar",
            "usage_percent",
            "expiry_date",
            "status_emoji",
            "status_text",
            "time_left_message",
            "is_trial",
            "not_trial_tariff",
            "is_active",
            "days_left",
            "hours_left",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_get_data_multiple_calls_same_email(
        self, mock_model_data, mock_dialog_manager, mock_cache, active_key
    ):
        """get_data() should work correctly on multiple calls"""
        mock_cache.keys.get.return_value = active_key
        mock_dialog_manager.middleware_data = {"cache": mock_cache}

        getter = KeyDetailsGetter()
        result1 = await getter.get_data(mock_dialog_manager)
        result2 = await getter.get_data(mock_dialog_manager)

        assert result1["error"] == result2["error"]
        assert result1["keys"] == result2["keys"]
        assert mock_cache.keys.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_data_different_emails(self, mock_model_data, mock_cache):
        """get_data() should fetch different keys for different emails"""
        key1 = Key(
            email="user1@example.com",
            inbound_id=12,
            client_id="c1",
            tg_id=123,
            key="key1",
            expiry_time=int(
                (datetime.utcnow() + timedelta(days=30)).timestamp() * 1000
            ),
            tariff_id=1,
        )
        key2 = Key(
            email="user2@example.com",
            inbound_id=13,
            client_id="c2",
            tg_id=456,
            key="key2",
            expiry_time=int(
                (datetime.utcnow() + timedelta(days=20)).timestamp() * 1000
            ),
            tariff_id=2,
        )

        async def side_effect(email):
            return key1 if email == "key_user1@example.com" else key2

        mock_cache.keys.get.side_effect = side_effect
        mock_cache.tariffs.get.return_value = None

        getter = KeyDetailsGetter()

        manager1 = AsyncMock()
        manager1.dialog_data = {"email": "user1@example.com"}
        manager1.middleware_data = {"cache": mock_cache}
        result1 = await getter.get_data(manager1)

        manager2 = AsyncMock()
        manager2.dialog_data = {"email": "user2@example.com"}
        manager2.middleware_data = {"cache": mock_cache}
        result2 = await getter.get_data(manager2)

        assert result1["keys"] == "key1"
        assert result2["keys"] == "key2"
