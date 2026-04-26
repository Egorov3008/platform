"""
Тесты для FormPaymentGetter (dialogs/windows/getters/payment/form_pay.py).

Покрытие:
- get_data: создаёт платёж, сохраняет payment_id в dialog_data, вызывает seter
- _get_payment_data: читает dialog_data или start_data
- seter: сохраняет PaymentModel в БД через payment_data.save_data

Стратегия:
- YooKassService и ServiceDataModel мокируются через AsyncMock
- DialogManager мокируется как в conftest (dialog_data dict, event.from_user.id)
- asyncpg.Pool — простой AsyncMock (не spec=asyncpg.Pool, чтобы избежать acquire chain)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dialogs.windows.getters.payment.form_pay import FormPaymentGetter
from models import PaymentModel


# ──────────────────────────────────────────────
# Фикстуры
# ──────────────────────────────────────────────

@pytest.fixture
def mock_yookassa_service():
    """Мок YooKassService."""
    svc = AsyncMock()
    svc.create_payment_form = AsyncMock(
        return_value={
            "payment_id": "yoo_pay_001",
            "confirmation_url": "https://yoomoney.ru/pay/001",
        }
    )
    return svc


@pytest.fixture
def mock_model_service():
    """Мок ServiceDataModel с атрибутом payments."""
    model = MagicMock()
    model.payments = AsyncMock()
    model.payments.save_data = AsyncMock()
    return model


@pytest.fixture
def mock_conn():
    """Мок asyncpg connection — не spec=Pool, чтобы избежать ошибок acquire chain."""
    return AsyncMock()


@pytest.fixture
def getter(mock_yookassa_service, mock_model_service, mock_conn):
    """FormPaymentGetter с мок-зависимостями."""
    return FormPaymentGetter(
        service=mock_yookassa_service,
        model_service=mock_model_service,
        conn=mock_conn,
    )


@pytest.fixture
def mock_manager():
    """Мок DialogManager с dialog_data, содержащим amount."""
    manager = AsyncMock()
    manager.dialog_data = {
        "amount": 500.0,
        "payment_type": "create_key",
        "number_of_months": 1,
    }
    manager.start_data = None
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 987654321
    return manager


# ──────────────────────────────────────────────
# get_data
# ──────────────────────────────────────────────

class TestGetData:
    @pytest.mark.asyncio
    async def test_returns_confirmation_url(self, getter, mock_manager):
        """get_data возвращает dict с confirmation_url."""
        result = await getter.get_data(mock_manager)
        assert result == {"confirmation_url": "https://yoomoney.ru/pay/001"}

    @pytest.mark.asyncio
    async def test_calls_create_payment_form_with_correct_args(
        self, getter, mock_yookassa_service, mock_manager
    ):
        """YooKassService.create_payment_form вызывается с amount и описанием."""
        await getter.get_data(mock_manager)

        mock_yookassa_service.create_payment_form.assert_awaited_once()
        call_args = mock_yookassa_service.create_payment_form.call_args
        assert call_args[0][0] == 500.0  # price
        assert "987654321" in call_args[1]["description"]

    @pytest.mark.asyncio
    async def test_stores_payment_id_in_dialog_data(self, getter, mock_manager):
        """payment_id сохраняется в dialog_manager.dialog_data."""
        await getter.get_data(mock_manager)
        assert mock_manager.dialog_data["payment_id"] == "yoo_pay_001"

    @pytest.mark.asyncio
    async def test_calls_seter(self, getter, mock_manager, mock_model_service, mock_conn):
        """Метод seter вызывается с payment_id, tg_id, amount."""
        with patch.object(getter, "seter", new=AsyncMock()) as mock_seter:
            await getter.get_data(mock_manager)

        mock_seter.assert_awaited_once_with("yoo_pay_001", 987654321, 500.0)

    @pytest.mark.asyncio
    async def test_missing_amount_raises_value_error(self, getter, mock_manager):
        """Если amount отсутствует ни в dialog_data, ни в start_data — бросает ValueError."""
        # Оба источника данных пусты — _data не содержит amount
        mock_manager.dialog_data = {}
        mock_manager.start_data = {}

        with pytest.raises(ValueError, match="Не указана сумма"):
            await getter.get_data(mock_manager)

    @pytest.mark.asyncio
    async def test_uses_tg_id_from_event(self, getter, mock_manager):
        """tg_id берётся из dialog_manager.event.from_user.id."""
        mock_manager.event.from_user.id = 111222333
        mock_manager.dialog_data["amount"] = 100.0

        await getter.get_data(mock_manager)

        call_args = getter.service.create_payment_form.call_args
        assert "111222333" in call_args[1]["description"]


# ──────────────────────────────────────────────
# _get_payment_data
# ──────────────────────────────────────────────

class TestGetPaymentData:
    def test_uses_dialog_data_when_present(self, getter, mock_manager):
        """Если dialog_data непустой — используется он."""
        mock_manager.dialog_data = {"amount": 300.0, "payment_type": "renew"}
        getter._get_payment_data(mock_manager)
        assert getter._data == {"amount": 300.0, "payment_type": "renew"}

    def test_falls_back_to_start_data(self, getter, mock_manager):
        """Если dialog_data пустой/None — используется start_data."""
        mock_manager.dialog_data = None
        mock_manager.start_data = {"amount": 150.0, "payment_type": "create_key"}
        getter._get_payment_data(mock_manager)
        assert getter._data == {"amount": 150.0, "payment_type": "create_key"}

    def test_empty_dialog_data_uses_start_data(self, getter, mock_manager):
        """Пустой dict dialog_data считается falsy — fallback на start_data."""
        mock_manager.dialog_data = {}
        mock_manager.start_data = {"amount": 200.0}
        getter._get_payment_data(mock_manager)
        # Пустой dict — falsy, поэтому используется start_data
        assert getter._data == {"amount": 200.0}


# ──────────────────────────────────────────────
# seter
# ──────────────────────────────────────────────

class TestSeter:
    @pytest.mark.asyncio
    async def test_saves_payment_model_to_db(
        self, getter, mock_model_service, mock_conn
    ):
        """seter создаёт PaymentModel и сохраняет её через payment_data.save_data."""
        getter._data = {
            "payment_type": "create_key",
            "number_of_months": 2,
        }

        await getter.seter("yoo_pay_999", 777888999, 250.0)

        mock_model_service.payments.save_data.assert_awaited_once()
        call_args = mock_model_service.payments.save_data.call_args
        # Первый аргумент — conn
        assert call_args[0][0] is mock_conn
        # Второй аргумент — PaymentModel
        payment: PaymentModel = call_args[0][1]
        assert isinstance(payment, PaymentModel)
        assert payment.payment_id == "yoo_pay_999"
        assert payment.tg_id == 777888999
        assert payment.amount == 250.0
        assert payment.status == "pending"

    @pytest.mark.asyncio
    async def test_seter_uses_payment_type_from_data(
        self, getter, mock_model_service, mock_conn
    ):
        """payment_type берётся из _data."""
        getter._data = {"payment_type": "renew_key", "number_of_months": 3}

        await getter.seter("pay_renew", 123, 99.0)

        call_args = mock_model_service.payments.save_data.call_args
        payment: PaymentModel = call_args[0][1]
        assert payment.payment_type == "renew_key"
        assert payment.number_of_months == 3

    @pytest.mark.asyncio
    async def test_seter_default_months_one(
        self, getter, mock_model_service, mock_conn
    ):
        """Если number_of_months не задан — по умолчанию 1."""
        getter._data = {"payment_type": "create_key"}

        await getter.seter("pay_default", 456, 50.0)

        call_args = mock_model_service.payments.save_data.call_args
        payment: PaymentModel = call_args[0][1]
        assert payment.number_of_months == 1

    @pytest.mark.asyncio
    async def test_seter_passes_payment_id_as_kwarg(
        self, getter, mock_model_service, mock_conn
    ):
        """save_data вызывается с payment_id как ключевым аргументом."""
        getter._data = {}

        await getter.seter("pay_kwarg_test", 100, 10.0)

        call_kwargs = mock_model_service.payments.save_data.call_args[1]
        assert call_kwargs.get("payment_id") == "pay_kwarg_test"
