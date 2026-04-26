import pytest
from unittest.mock import AsyncMock

from models.payments.payment import PaymentModel
from models.users.user import User
from services.core.data.service import ServiceDataModel
from services.cache.service import CacheService
from services.core.payment.processor import PaymentProcessor


@pytest.fixture
def mock_conn():
    """Фикстура для мока подключения к базе данных."""
    return AsyncMock()


@pytest.fixture
def mock_model_service():
    """Фикстура для мока сервиса данных."""
    model_service = AsyncMock(spec=ServiceDataModel)

    # Настраиваем моки для payments, users и tariffs
    model_service.payments = AsyncMock()
    model_service.users = AsyncMock()
    model_service.tariffs = AsyncMock()

    return model_service


@pytest.fixture
def mock_cache():
    """Фикстура для мока сервиса кеширования."""
    cache = AsyncMock(spec=CacheService)
    cache.payments = AsyncMock()
    return cache


@pytest.fixture
def payment_processor(mock_conn, mock_model_service, mock_cache):
    """Фикстура для создания экземпляра PaymentProcessor."""
    return PaymentProcessor(mock_conn, mock_model_service, mock_cache)


@pytest.fixture
def sample_payment_data():
    """Фикстура для создания тестовых данных платежа."""
    return PaymentModel(
        payment_id="test_payment_123",
        amount=99.99,
        payment_type="create_key|1",
        tg_id=123456789,
    )


@pytest.fixture
def sample_user_data():
    """Фикстура для создания тестовых данных пользователя."""
    return User(tg_id=123456789, server_id=1, username="test_user")
