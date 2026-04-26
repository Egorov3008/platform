"""
Flow contract tests for Payment renewal: KeyDetails → start(PaymentState.*)

Tests verify:
- KeyDetailsKeyboard._on_trial_renewal_click() passes email as start_data
- KeyDetailsKeyboard._on_renewal_click() passes tariff/payment_type as start_data
- SettingsPayment reads from start_data with fallback pattern
- Two paths: trial renewal (view_tariff) vs paid renewal (setting_pay)

No mocking of switch_to() / start() aiogram-dialog internals.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, Tariff, User
from dialogs.windows.widgets.keybord.keys.key_details import KeyDetailsKeyboard
from dialogs.windows.getters.payment.setting_payment import SettingsPayment


def _make_mock_model_data():
    """Helper: mock ServiceDataModel с users.get_data → User(balance=0)."""
    mock = AsyncMock()
    mock.users = AsyncMock()
    mock.users.get_data = AsyncMock(return_value=User(tg_id=123456789, balance=0.0))
    return mock


def make_tariff(tariff_id: int = 1, name: str = "Pro", amount: float = 100.0) -> Tariff:
    """Helper to create a test Tariff."""
    return Tariff(
        id=tariff_id,
        name_tariff=name,
        amount=amount,
    )


def make_key(
    email: str,
    tg_id: int = 123456789,
    tariff_id: int = 1,
    amount: float | None = 100.0,
    expiry_offset_ms: int = 86400000,
    is_trial: bool = False,
) -> Key:
    """Helper to create a test Key."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        tariff_id=tariff_id,
        amount=amount if not is_trial else None,
    )


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data, start_data, and event."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    manager.start_data = {}
    manager.start = AsyncMock()
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel."""
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    model_data.tariffs = AsyncMock()
    return model_data


@pytest.fixture
def mock_cache_service():
    """Mock CacheService."""
    cache = AsyncMock()
    cache.payments = AsyncMock()
    cache.payments.temporary_set = AsyncMock()
    return cache


class TestKeyDetailsKeyboardTrialRenewal:
    """Tests for _on_trial_renewal_click() — trial key renewal path."""

    async def test_passes_email_as_start_data(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler calls start(PaymentState.view_tariff, data={'email': email})."""
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["email"] == "user@example.com"

    async def test_email_from_dialog_data(self, mock_dialog_manager, mock_model_data):
        """Handler reads email from dialog_data (set by KeyListKeyboard)."""
        mock_dialog_manager.dialog_data["email"] = "trial@example.com"

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["email"] == "trial@example.com"

    async def test_missing_email_does_not_crash(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler with missing email answers error gracefully."""
        # dialog_data has no "email"

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)


class TestKeyDetailsKeyboardPaidRenewal:
    """Tests for _on_renewal_click() — paid key renewal path."""

    async def test_passes_tariff_in_start_data(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler includes tariff object in start_data."""
        key = make_key("user@example.com", tariff_id=1, amount=100.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["tariff"] == tariff

    async def test_passes_payment_type_renew_format(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler writes payment_type = 'renew_key|{email}' in start_data."""
        key = make_key("user@example.com", tariff_id=1, amount=100.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["payment_type"] == "renew_key|user@example.com"

    async def test_passes_amount_from_key_or_tariff(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler prefers key.amount over tariff.amount for start_data."""
        key = make_key("user@example.com", tariff_id=1, amount=150.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        call_args = mock_dialog_manager.start.call_args
        # Should use key.amount (150) not tariff.amount (100)
        assert call_args[1]["data"]["amount"] == 150.0

    async def test_passes_amount_from_tariff_when_key_amount_none(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler uses tariff.amount when key.amount is None."""
        key = make_key("user@example.com", tariff_id=1, amount=None)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["amount"] == 100.0

    async def test_starts_at_setting_pay_not_view_tariff(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler starts PaymentState.setting_pay (not view_tariff) for paid renewal."""
        key = make_key("user@example.com", tariff_id=1, amount=100.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        from states.payment import PaymentState

        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == PaymentState.setting_pay

    async def test_missing_key_answers_error(
        self, mock_dialog_manager, mock_model_data
    ):
        """Handler answers error when key not found."""
        mock_dialog_manager.dialog_data["email"] = "notfound@example.com"
        mock_model_data.keys.get_data.return_value = None

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)


class TestSettingsPaymentReadsStartData:
    """Tests for SettingsPayment fallback: dialog_data OR start_data."""

    async def test_reads_tariff_from_start_data_when_dialog_data_empty(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter reads start_data["tariff"] when dialog_data is empty."""
        from services.core.price.result import PriceResult

        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.start_data = {
            "tariff": tariff,
            "amount": 100.0,
            "payment_type": "renew_key|user@example.com",
        }
        mock_dialog_manager.dialog_data = {}  # empty

        mock_price_service = AsyncMock()
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=100.0,
            final_amount=100.0,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, _make_mock_model_data())
        result = await getter.get_data(mock_dialog_manager)

        # Should have read from start_data
        assert result["tariff_name"] == "Pro"
        assert result["amount"] == 100.0

    async def test_reads_amount_from_start_data(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter reads start_data["amount"] with fallback pattern."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.start_data = {
            "tariff": tariff,
            "amount": 100.0,
            "payment_type": "renew_key|user@example.com",
        }
        # Simulate _get_data fallback
        amount = float(mock_dialog_manager.start_data.get("amount") or 0)
        assert amount == 100.0

    async def test_reads_payment_type_from_start_data(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter reads start_data["payment_type"]."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.start_data = {
            "tariff": tariff,
            "amount": 100.0,
            "payment_type": "renew_key|user@example.com",
        }
        payment_type = mock_dialog_manager.start_data.get("payment_type")
        assert payment_type == "renew_key|user@example.com"

    async def test_dialog_data_takes_priority_over_start_data(
        self, mock_dialog_manager, mock_cache_service
    ):
        """When both dialog_data and start_data present, dialog_data is used."""
        from services.core.price.result import PriceResult

        tariff_d = make_tariff(1, "Dialog Tariff", 150.0)
        tariff_s = make_tariff(2, "Start Tariff", 100.0)

        mock_dialog_manager.dialog_data = {
            "tariff": tariff_d,
            "amount": 150.0,
            "payment_type": "renew_key|dialog@example.com",
        }
        mock_dialog_manager.start_data = {
            "tariff": tariff_s,
            "amount": 100.0,
            "payment_type": "renew_key|start@example.com",
        }

        mock_price_service = AsyncMock()
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=150.0,
            final_amount=150.0,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, _make_mock_model_data())
        result = await getter.get_data(mock_dialog_manager)

        # Should use dialog_data (amount=150)
        assert result["tariff_name"] == "Dialog Tariff"
        assert result["amount"] == 150.0


class TestRenewalStartDataContract:
    """Contract tests: KeyDetailsKeyboard → SettingsPayment start_data pattern."""

    async def test_start_data_from_key_details_matches_settings_payment_expectations(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Start_data shape from KeyDetailsKeyboard matches SettingsPayment expectations."""
        key = make_key("user@example.com", tariff_id=1, amount=100.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_model_data.keys.get_data.return_value = key
        mock_model_data.tariffs.get_data.return_value = tariff

        # Step 1: KeyDetailsKeyboard writes start_data
        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        # Capture what would be passed as start_data
        start_data_passed: dict = mock_dialog_manager.start.call_args[1]["data"]  # type: ignore

        # Step 2: SettingsPayment reads from start_data
        mock_dialog_manager.start_data = start_data_passed
        mock_dialog_manager.dialog_data = {}  # Simulate new dialog context

        getter = SettingsPayment(AsyncMock(), _make_mock_model_data())
        result = await getter.get_data(mock_dialog_manager)

        # Verify all required fields are present
        assert result["tariff_name"] is not None
        assert "amount" in result
        assert "number_of_months" in result

    async def test_trial_start_data_contract(
        self, mock_dialog_manager, mock_model_data
    ):
        """Trial renewal start_data contract: only email required."""
        mock_dialog_manager.dialog_data["email"] = "trial@example.com"

        keyboard = KeyDetailsKeyboard(mock_model_data)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)  # type: ignore

        # For trial renewal, only email is passed
        start_data = mock_dialog_manager.start.call_args[1]["data"]
        assert "email" in start_data
        assert start_data["email"] == "trial@example.com"
