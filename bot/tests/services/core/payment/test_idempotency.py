"""Тесты идемпотентности обработки платежей."""

import pytest
from unittest.mock import AsyncMock

from services.core.payment.router import PaymentRouter
from services.core.payment.processor import PaymentProcessor
from services.core.payment.creation_service import KeyCreationService
from services.core.payment.renewal_service import KeyRenewalService


@pytest.mark.asyncio
async def test_idempotency_skips_succeeded_payment():
    """route() пропускает платёж с status='succeeded' — creation_service.process() не вызван."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    # Платёж уже обработан
    processor.status = "succeeded"

    router = PaymentRouter(processor, creation_service, renewal_service)
    await router.route("payment_123")

    processor.load_payment_data.assert_called_once_with("payment_123")
    creation_service.process.assert_not_called()
    renewal_service.process.assert_not_called()
    processor.update_payment.assert_not_called()
    processor.extract_operation.assert_not_called()


@pytest.mark.asyncio
async def test_idempotency_processes_pending_payment():
    """route() обрабатывает платёж с status='pending'."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.status = "pending"
    processor.extract_operation.return_value = ("create_key", "1")
    processor.referral_discount = 0

    router = PaymentRouter(processor, creation_service, renewal_service)
    await router.route("payment_456")

    processor.load_payment_data.assert_called_once_with("payment_456")
    creation_service.process.assert_called_once_with(tariff_id="1")
    processor.update_payment.assert_called_once_with("payment_456")


@pytest.mark.asyncio
async def test_idempotency_processes_canceled_payment():
    """route() обрабатывает платёж с status='canceled' (не пропускает)."""
    processor = AsyncMock(spec=PaymentProcessor)
    creation_service = AsyncMock(spec=KeyCreationService)
    renewal_service = AsyncMock(spec=KeyRenewalService)

    processor.status = "canceled"
    processor.extract_operation.return_value = ("renew_key", "user@example.com")
    processor.referral_discount = 0

    router = PaymentRouter(processor, creation_service, renewal_service)
    await router.route("payment_789")

    processor.load_payment_data.assert_called_once_with("payment_789")
    renewal_service.process.assert_called_once_with(email="user@example.com")
    processor.update_payment.assert_called_once_with("payment_789")
