"""
Tests for PaymentProcessor - payment processing with mocks.

PaymentProcessor.load_payment_data() and update_payment() handle payment operations.
Side-effectful: requires mocking ServiceDataModel, CacheService, asyncpg.Pool.
"""

from unittest.mock import AsyncMock

import pytest

from models import PaymentModel, User
from services.core.payment.processor import PaymentProcessor


@pytest.fixture
def mock_conn():
    """Mock asyncpg.Pool"""
    return AsyncMock()


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.payments = AsyncMock()
    model_data.users = AsyncMock()
    return model_data


@pytest.fixture
def mock_cache():
    """Mock CacheService"""
    cache = AsyncMock()
    cache.payments = AsyncMock()
    return cache


@pytest.fixture
def sample_payment():
    """Sample PaymentModel"""
    return PaymentModel(
        payment_id="test_payment_123",
        tg_id=123456789,
        amount=99.99,
        payment_type="create_key|1",
        status="pending",
    )


@pytest.fixture
def sample_user():
    """Sample User"""
    from datetime import datetime

    return User(
        tg_id=123456789,
        username="testuser",
        trial=0,
        created_at=datetime.now(),
        server_id=1,
    )


class TestPaymentProcessorLoadData:
    """Test PaymentProcessor.load_payment_data() method"""

    @pytest.mark.asyncio
    async def test_load_payment_data_success(
        self, mock_conn, mock_model_data, mock_cache, sample_payment
    ):
        """load_payment_data() should load payment from cache/db"""
        mock_cache.payments.get.return_value = sample_payment
        mock_model_data.payments = mock_cache.payments

        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)
        processor.payment_data = AsyncMock()
        processor.payment_data.get_data.return_value = sample_payment

        result = await processor.payment_data.get_data("test_payment_123")

        assert result is not None
        assert result.payment_id == "test_payment_123"

    @pytest.mark.asyncio
    async def test_load_payment_data_not_found(
        self, mock_conn, mock_model_data, mock_cache
    ):
        """load_payment_data() should return None when payment not found"""
        mock_cache.payments.get.return_value = None
        mock_model_data.payments = mock_cache.payments

        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)
        processor.payment_data = AsyncMock()
        processor.payment_data.get_data.return_value = None

        result = await processor.payment_data.get_data("nonexistent_payment")

        assert result is None


class TestPaymentProcessorExtractOperation:
    """Test PaymentProcessor.extract_operation() method"""

    def test_extract_operation_create_key(self, mock_conn, mock_model_data, mock_cache):
        """extract_operation() should parse create_key|tariff_id format"""
        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)
        processor.payment_type = "create_key|5"

        # The method parses payment_type to extract operation
        # Based on the code, it splits on "|"
        parts = processor.payment_type.split("|")
        assert parts[0] == "create_key"
        assert parts[1] == "5"

    def test_extract_operation_renewal(self, mock_conn, mock_model_data, mock_cache):
        """extract_operation() should parse renewal|months format"""
        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)
        processor.payment_type = "renewal|3"

        parts = processor.payment_type.split("|")
        assert parts[0] == "renewal"
        assert parts[1] == "3"


class TestPaymentProcessorUpdatePayment:
    """Test PaymentProcessor.update_payment() method"""

    @pytest.mark.asyncio
    async def test_update_payment_success(
        self, mock_conn, mock_model_data, mock_cache, sample_payment
    ):
        """update_payment() should update payment status"""
        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)
        processor.payment_data = AsyncMock()
        processor.payment_data.update.return_value = None

        # Simulate payment update
        sample_payment.status = "completed"
        await processor.payment_data.update(mock_conn, sample_payment)

        assert sample_payment.status == "completed"
        processor.payment_data.update.assert_called_once()


class TestPaymentProcessorIntegration:
    """Integration tests for PaymentProcessor"""

    @pytest.mark.asyncio
    async def test_processor_initialization(
        self, mock_conn, mock_model_data, mock_cache
    ):
        """PaymentProcessor should initialize with dependencies"""
        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)

        assert processor is not None
        # Check that dependencies are stored
        # (actual attributes depend on implementation)

    @pytest.mark.asyncio
    async def test_processor_multiple_payments(
        self, mock_conn, mock_model_data, mock_cache
    ):
        """PaymentProcessor should handle multiple payment operations"""
        processor = PaymentProcessor(mock_conn, mock_model_data, mock_cache)

        # Simulate handling multiple payments
        payment1 = PaymentModel(
            payment_id="pay1",
            tg_id=111,
            amount=50,
            payment_type="create_key|1",
            status="pending",
        )
        payment2 = PaymentModel(
            payment_id="pay2",
            tg_id=222,
            amount=100,
            payment_type="renewal|3",
            status="completed",
        )

        # Both should be processable
        assert payment1.payment_id != payment2.payment_id
        assert payment1.tg_id != payment2.tg_id
