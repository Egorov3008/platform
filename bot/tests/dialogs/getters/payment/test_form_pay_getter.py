"""
Тесты для FormPaymentGetter (dialogs/windows/getters/payment/form_pay.py).

После миграции FormPaymentGetter использует BackendAPIClient вместо YooKassService.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dialogs.windows.getters.payment.form_pay import FormPaymentGetter


@pytest.fixture
def payment_response():
    """Default response for backend_client.create_payment used by these tests."""
    return {
        "payment_id": "backend_pay_001",
        "confirmation_url": "https://yoomoney.ru/pay/001",
        "amount": 500.0,
    }


@pytest.fixture
def mock_backend_client(mock_backend_client, payment_response):
    """Override the shared mock with payment-specific create_payment return value."""
    mock_backend_client.create_payment = AsyncMock(return_value=payment_response)
    return mock_backend_client


@pytest.fixture
def getter(mock_backend_client):
    return FormPaymentGetter(backend_client=mock_backend_client)


@pytest.fixture
def mock_tariff():
    t = MagicMock()
    t.id = 5
    t.name_tariff = "Pro"
    t.amount = 500.0
    return t


@pytest.fixture
def mock_manager(mock_tariff):
    manager = AsyncMock()
    manager.dialog_data = {
        "amount": 500.0,
        "payment_type": "create_key|5",
        "number_of_months": 1,
        "tariff": mock_tariff,
    }
    manager.start_data = None
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 987654321
    return manager


class TestGetData:
    @pytest.mark.asyncio
    async def test_returns_confirmation_url(self, getter, mock_manager):
        result = await getter.get_data(mock_manager)
        assert result == {"confirmation_url": "https://yoomoney.ru/pay/001"}

    @pytest.mark.asyncio
    async def test_calls_backend_create_payment(
        self, getter, mock_manager, mock_backend_client
    ):
        await getter.get_data(mock_manager)

        mock_backend_client.create_payment.assert_awaited_once()
        call_kwargs = mock_backend_client.create_payment.call_args[1]
        assert call_kwargs["tg_id"] == 987654321
        assert call_kwargs["tariff_id"] == 5
        assert call_kwargs["operation"] == "create_key"
        assert call_kwargs["amount"] == 500.0

    @pytest.mark.asyncio
    async def test_stores_payment_id_and_url_in_dialog_data(
        self, getter, mock_manager
    ):
        await getter.get_data(mock_manager)
        assert mock_manager.dialog_data["payment_id"] == "backend_pay_001"
        assert mock_manager.dialog_data["confirmation_url"] == "https://yoomoney.ru/pay/001"

    @pytest.mark.asyncio
    async def test_renew_key_operation(self, getter, mock_manager, mock_backend_client):
        mock_manager.dialog_data["payment_type"] = "renew_key|user@example.com"
        await getter.get_data(mock_manager)

        call_kwargs = mock_backend_client.create_payment.call_args[1]
        assert call_kwargs["operation"] == "renew_key"
        assert call_kwargs["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_missing_amount_raises_value_error(self, getter, mock_manager):
        mock_manager.dialog_data = {}
        mock_manager.start_data = {}

        with pytest.raises(ValueError, match="Не указана сумма"):
            await getter.get_data(mock_manager)

    @pytest.mark.asyncio
    async def test_reuses_existing_pending_payment(
        self, getter, mock_manager, mock_backend_client
    ):
        """Если в dialog_data уже есть payment_id и статус pending — новый не создаётся."""
        mock_manager.dialog_data["payment_id"] = "existing_pay"
        mock_manager.dialog_data["confirmation_url"] = "https://existing.url"
        mock_backend_client.get_payment_status = AsyncMock(return_value="pending")

        result = await getter.get_data(mock_manager)

        mock_backend_client.create_payment.assert_not_awaited()
        assert result == {"confirmation_url": "https://existing.url"}

    @pytest.mark.asyncio
    async def test_creates_new_payment_if_existing_succeeded(
        self, getter, mock_manager, mock_backend_client
    ):
        """Если существующий платёж succeeded — создаётся новый."""
        mock_manager.dialog_data["payment_id"] = "old_pay"
        mock_manager.dialog_data["confirmation_url"] = "https://old.url"
        mock_backend_client.get_payment_status = AsyncMock(return_value="succeeded")

        result = await getter.get_data(mock_manager)

        mock_backend_client.create_payment.assert_awaited_once()
        assert result == {"confirmation_url": "https://yoomoney.ru/pay/001"}


class TestGetPaymentData:
    def test_uses_dialog_data_when_present(self, getter, mock_manager):
        mock_manager.dialog_data = {"amount": 300.0, "payment_type": "renew"}
        getter._get_payment_data(mock_manager)
        assert getter._data == {"amount": 300.0, "payment_type": "renew"}

    def test_falls_back_to_start_data(self, getter, mock_manager):
        mock_manager.dialog_data = None
        mock_manager.start_data = {"amount": 150.0, "payment_type": "create_key"}
        getter._get_payment_data(mock_manager)
        assert getter._data == {"amount": 150.0, "payment_type": "create_key"}

    def test_empty_dialog_data_uses_start_data(self, getter, mock_manager):
        mock_manager.dialog_data = {}
        mock_manager.start_data = {"amount": 200.0}
        getter._get_payment_data(mock_manager)
        assert getter._data == {"amount": 200.0}
