"""
Tests for KeyUpdater service - pure key update logic.

KeyUpdater.refresh_key() updates Key dataclass fields based on Tariff.
Pure logic: mutates key object, no I/O, delegates expiry calculation.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from models import Key, Tariff, Server
from services.core.keys.utils.calculator import ExpiryCalculator
from services.core.keys.utils.updating import KeyUpdater


@pytest.fixture
def expiry_calculator():
    """Real ExpiryCalculator for testing"""
    return ExpiryCalculator()


@pytest.fixture
def sample_key():
    """Sample Key for mutation testing"""
    return Key(
        email="test@example.com",
        inbound_id=12,
        client_id="client123",
        tg_id=123456789,
        key="test_key_data",
        expiry_time=int(datetime.now().timestamp() * 1000),
        tariff_id=1,
    )


@pytest.fixture
def sample_tariff():
    """Sample Tariff for update"""
    return Tariff(
        id=5,
        name_tariff="Premium",
        period=30,
        traffic_limit=Decimal("100"),  # 100 GB
        limit_ip=5,
    )


@pytest.fixture
def sample_server():
    """Sample Server for assignment"""
    return Server(
        id=1,
        server_name="Test Server",
        api_url="https://api.test.com",
        login="admin",
        password="pass",
        subscription_url="https://sub.test.com",
        cluster_name="cluster1",
    )


class TestKeyUpdaterBasic:
    """Test basic KeyUpdater.refresh_key() functionality"""

    def test_refresh_key_updates_tariff_id(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should update tariff_id"""
        updater = KeyUpdater(expiry_calculator)
        original_tariff_id = sample_key.tariff_id

        result = updater.refresh_key(
            sample_key, sample_tariff, sample_server, number_of_months=1
        )

        assert result.tariff_id == 5
        assert result.tariff_id != original_tariff_id

    def test_refresh_key_updates_tariff_name(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should update tariff name"""
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        assert result.name_tariff == "Premium"

    def test_refresh_key_updates_limit_ip(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should update limit_ip from tariff"""
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        assert result.limit_ip == 5

    def test_refresh_key_updates_server_info(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should assign server_info"""
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        assert result.server_info == sample_server

    def test_refresh_key_resets_used_traffic(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should reset used_traffic to 0"""
        updater = KeyUpdater(expiry_calculator)
        sample_key.used_traffic = 50.5  # Simulate some used traffic

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        assert result.used_traffic == 0.0

    def test_refresh_key_returns_key_object(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should return the same Key object (mutated)"""
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        assert result is sample_key  # Same object reference


class TestKeyUpdaterTrafficCalculation:
    """Test total_gb calculation based on traffic_limit and months"""

    def test_refresh_key_calculates_total_gb_single_month(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should calculate total_gb for 1 month"""
        # traffic_limit = 100 GB, 1 month
        # total_gb = 100 * 2^30 * 1 = 100 * 1073741824 bytes
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(
            sample_key, sample_tariff, sample_server, number_of_months=1
        )

        expected = int(Decimal("100") * (2**30) * 1)
        assert result.total_gb == expected

    def test_refresh_key_calculates_total_gb_multiple_months(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should calculate total_gb for multiple months"""
        # traffic_limit = 100 GB, 3 months
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(
            sample_key, sample_tariff, sample_server, number_of_months=3
        )

        expected = int(Decimal("100") * (2**30) * 3)
        assert result.total_gb == expected

    def test_refresh_key_calculates_total_gb_zero_traffic(
        self, expiry_calculator, sample_key, sample_server
    ):
        """refresh_key() with zero traffic_limit"""
        tariff = Tariff(
            id=10, name_tariff="Free", period=30, traffic_limit=Decimal("0"), limit_ip=1
        )
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(
            sample_key, tariff, sample_server, number_of_months=1
        )

        assert result.total_gb == 0


class TestKeyUpdaterExpiryCalculation:
    """Test expiry_time calculation delegates to ExpiryCalculator"""

    def test_refresh_key_updates_expiry_time(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should update expiry_time via ExpiryCalculator"""
        updater = KeyUpdater(expiry_calculator)
        original_expiry = sample_key.expiry_time

        result = updater.refresh_key(
            sample_key, sample_tariff, sample_server, number_of_months=1
        )

        # Expiry should be updated (and likely different from original)
        assert result.expiry_time != original_expiry
        # Should be a reasonable future timestamp
        assert result.expiry_time > original_expiry

    def test_refresh_key_expiry_respects_months(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() with different months should give different expiry times"""
        updater = KeyUpdater(expiry_calculator)

        result_1month = updater.refresh_key(
            Key(**sample_key.to_dict()),  # Copy
            sample_tariff,
            sample_server,
            number_of_months=1,
        )
        result_3months = updater.refresh_key(
            Key(**sample_key.to_dict()),  # Copy
            sample_tariff,
            sample_server,
            number_of_months=3,
        )

        # 3-month key should have later expiry
        assert result_3months.expiry_time > result_1month.expiry_time


class TestKeyUpdaterWithoutServer:
    """Test refresh_key() when server is None"""

    def test_refresh_key_none_server(
        self, expiry_calculator, sample_key, sample_tariff
    ):
        """refresh_key() should handle server=None"""
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(sample_key, sample_tariff, server=None)

        # Should still update other fields
        assert result.tariff_id == 5
        assert result.name_tariff == "Premium"
        # server_info should be None
        assert result.server_info is None


class TestKeyUpdaterMutation:
    """Test that refresh_key() mutates the key object in place"""

    def test_refresh_key_mutates_original(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """refresh_key() should mutate the original key object"""
        updater = KeyUpdater(expiry_calculator)
        key_id = id(sample_key)  # Get object identity

        result = updater.refresh_key(sample_key, sample_tariff, sample_server)

        # Should be the same object
        assert id(result) == key_id
        # Original should be mutated
        assert sample_key.tariff_id == 5
        assert sample_key.name_tariff == "Premium"

    def test_refresh_key_idempotent_fields_except_expiry(
        self, expiry_calculator, sample_key, sample_tariff, sample_server
    ):
        """Calling refresh_key twice with same tariff should preserve most fields"""
        updater = KeyUpdater(expiry_calculator)

        result1 = updater.refresh_key(sample_key, sample_tariff, sample_server)
        tariff_id_after_first = result1.tariff_id

        # Create a fresh key with same initial data
        key2 = Key(**sample_key.to_dict())
        result2 = updater.refresh_key(key2, sample_tariff, sample_server)
        tariff_id_after_second = result2.tariff_id

        # tariff_id should be the same
        assert tariff_id_after_first == tariff_id_after_second


class TestKeyUpdaterValidation:
    """Test KeyUpdater behavior with various inputs"""

    def test_refresh_key_with_small_traffic(
        self, expiry_calculator, sample_key, sample_server
    ):
        """refresh_key() with small traffic_limit"""
        tariff = Tariff(
            id=20,
            name_tariff="Micro",
            period=7,
            traffic_limit=Decimal("0.5"),  # 512 MB
            limit_ip=1,
        )
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(
            sample_key, tariff, sample_server, number_of_months=1
        )

        assert result.name_tariff == "Micro"
        assert result.total_gb == int(Decimal("0.5") * (2**30))

    def test_refresh_key_with_large_traffic(
        self, expiry_calculator, sample_key, sample_server
    ):
        """refresh_key() with large traffic_limit"""
        tariff = Tariff(
            id=30,
            name_tariff="Enterprise",
            period=30,
            traffic_limit=Decimal("1000"),  # 1 TB
            limit_ip=20,
        )
        updater = KeyUpdater(expiry_calculator)

        result = updater.refresh_key(
            sample_key, tariff, sample_server, number_of_months=1
        )

        assert result.name_tariff == "Enterprise"
        assert result.limit_ip == 20
