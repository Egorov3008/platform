import pytest
from unittest.mock import AsyncMock

from services.core.payment.router import PaymentRouter
from services.core.payment.processor import PaymentProcessor
from services.core.payment.creation_service import KeyCreationService
from services.core.payment.renewal_service import KeyRenewalService


def test_payment_router_initialization():
    """Тест инициализации PaymentRouter."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    router = PaymentRouter(processor, creation_service, renewal_service)

    assert router.processor == processor
    assert router.creation_service == creation_service
    assert router.renewal_service == renewal_service


@pytest.mark.asyncio
async def test_route_create_key():
    """Тест маршрутизации на создание ключа."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.extract_operation.return_value = ("create_key", "1")
    processor.status = "pending"
    processor.referral_discount = 0

    router = PaymentRouter(processor, creation_service, renewal_service)

    await router.route("test_payment_123")

    processor.load_payment_data.assert_called_once_with("test_payment_123")
    processor.extract_operation.assert_called_once()
    creation_service.process.assert_called_once_with(tariff_id="1")
    renewal_service.process.assert_not_called()
    processor.update_payment.assert_called_once_with("test_payment_123")


@pytest.mark.asyncio
async def test_route_renew_key():
    """Тест маршрутизации на продление ключа."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.extract_operation.return_value = ("renew_key", "user@example.com")
    processor.status = "pending"
    processor.referral_discount = 0

    router = PaymentRouter(processor, creation_service, renewal_service)

    await router.route("test_payment_123")

    processor.load_payment_data.assert_called_once_with("test_payment_123")
    processor.extract_operation.assert_called_once()
    creation_service.process.assert_not_called()
    renewal_service.process.assert_called_once_with(email="user@example.com")
    processor.update_payment.assert_called_once_with("test_payment_123")


@pytest.mark.asyncio
async def test_route_unknown_operation():
    """Тест маршрутизации с неизвестной операцией."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.extract_operation.return_value = ("unknown_operation", "test_data")
    processor.status = "pending"

    router = PaymentRouter(processor, creation_service, renewal_service)

    with pytest.raises(ValueError, match="Неизвестный тип операции: unknown_operation"):
        await router.route("test_payment_123")

    processor.load_payment_data.assert_called_once_with("test_payment_123")
    processor.extract_operation.assert_called_once()
    creation_service.process.assert_not_called()
    renewal_service.process.assert_not_called()
    processor.update_payment.assert_not_called()


@pytest.mark.asyncio
async def test_route_exception_handling():
    """Тест обработки исключения при маршрутизации."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.load_payment_data.side_effect = Exception("Database connection failed")

    router = PaymentRouter(processor, creation_service, renewal_service)

    with pytest.raises(Exception, match="Database connection failed"):
        await router.route("test_payment_123")

    processor.load_payment_data.assert_called_once_with("test_payment_123")
    processor.extract_operation.assert_not_called()
    creation_service.process.assert_not_called()
    renewal_service.process.assert_not_called()
    processor.update_payment.assert_not_called()


@pytest.mark.asyncio
async def test_route_skips_already_succeeded_payment():
    """Тест идемпотентности: повторный вебхук не создаёт дубликат."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.status = "succeeded"

    router = PaymentRouter(processor, creation_service, renewal_service)

    await router.route("test_payment_123")

    processor.load_payment_data.assert_called_once_with("test_payment_123")
    processor.extract_operation.assert_not_called()
    creation_service.process.assert_not_called()
    renewal_service.process.assert_not_called()
    processor.update_payment.assert_not_called()
