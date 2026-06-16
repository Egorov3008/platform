"""
Flow contract tests for Payment renewal: KeyDetails → start(PaymentState.*)

Source: dialogs/windows/widgets/keybord/keys/key_details.py
        dialogs/windows/getters/payment/setting_payment.py

Contract:
- KeyDetailsKeyboard._on_trial_renewal_click passes email as start_data and
  switches to PaymentState.view_tariff.
- KeyDetailsKeyboard._on_renewal_click loads key+tariff via backend, then
  passes {email, payment_type, amount, tariff, number_of_months} to
  PaymentState.setting_pay.
- SettingsPayment reads from dialog_data (preferred) or start_data.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, Tariff
from dialogs.windows.widgets.keybord.keys.key_details import KeyDetailsKeyboard
from dialogs.windows.getters.payment.setting_payment import SettingsPayment


def make_tariff(tariff_id: int = 1, name: str = "Pro", amount: float = 100.0) -> Tariff:
    """Helper to create a test Tariff."""
    return Tariff(
        id=tariff_id,
        name_tariff=name,
        amount=amount,
    )


def make_key_dict(
    email: str,
    tg_id: int = 123456789,
    tariff_id: int = 1,
    expiry_offset_ms: int = 86400000,
) -> dict:
    """Build a backend-shaped dict for a Key."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "email": email,
        "tg_id": tg_id,
        "client_id": "c1",
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "tariff_id": tariff_id,
    }


def make_tariff_dict(tariff_id: int = 1, name: str = "Pro", amount: float = 100.0) -> dict:
    """Build a backend-shaped dict for a Tariff."""
    return {
        "id": tariff_id,
        "name_tariff": name,
        "amount": amount,
    }


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
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.get_key_details = AsyncMock(return_value=None)
    backend.get_tariff = AsyncMock(return_value=None)
    backend.get_user = AsyncMock(return_value=None)
    return backend


# ---------------------------------------------------------------------------
# KeyDetailsKeyboard — trial renewal
# ---------------------------------------------------------------------------


class TestKeyDetailsKeyboardTrialRenewal:
    """Tests for _on_trial_renewal_click() — trial key renewal path."""

    async def test_passes_email_as_start_data(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler calls start(PaymentState.view_tariff, data={'email': email})."""
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["email"] == "user@example.com"

    async def test_email_from_dialog_data(self, mock_dialog_manager, mock_backend):
        """Handler reads email from dialog_data (set by KeyListKeyboard)."""
        mock_dialog_manager.dialog_data["email"] = "trial@example.com"

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["email"] == "trial@example.com"

    async def test_missing_email_does_not_crash(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler with missing email answers error gracefully."""
        # dialog_data has no "email"
        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)


# ---------------------------------------------------------------------------
# KeyDetailsKeyboard — paid renewal
# ---------------------------------------------------------------------------


class TestKeyDetailsKeyboardPaidRenewal:
    """Tests for _on_renewal_click() — paid key renewal path."""

    async def test_passes_tariff_in_start_data(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler includes tariff object in start_data."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["tariff"] == tariff

    async def test_passes_payment_type_renew_format(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler writes payment_type = 'renew_key|{email}' in start_data."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["payment_type"] == "renew_key|user@example.com"

    async def test_passes_amount_from_tariff(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler uses tariff.amount for start_data (current source behaviour)."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        call_args = mock_dialog_manager.start.call_args
        # Source: amount comes from tariff.amount
        assert call_args[1]["data"]["amount"] == 100.0

    async def test_starts_at_setting_pay_not_view_tariff(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler starts PaymentState.setting_pay (not view_tariff) for paid renewal."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        from states.payment import PaymentState

        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == PaymentState.setting_pay

    async def test_missing_key_answers_error(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler answers error when key not found."""
        mock_dialog_manager.dialog_data["email"] = "notfound@example.com"
        mock_backend.get_key_details.return_value = None

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)

    async def test_passes_number_of_months_default(
        self, mock_dialog_manager, mock_backend
    ):
        """Handler sets number_of_months=1 by default in start_data."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        call_args = mock_dialog_manager.start.call_args
        assert call_args[1]["data"]["number_of_months"] == 1


# ---------------------------------------------------------------------------
# SettingsPayment — reads from start_data
# ---------------------------------------------------------------------------


class TestSettingsPaymentReadsStartData:
    """Tests for SettingsPayment fallback: dialog_data OR start_data."""

    async def test_reads_tariff_from_start_data_when_dialog_data_empty(
        self, mock_dialog_manager, mock_backend
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
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        mock_price_service = AsyncMock()
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=100.0,
            final_amount=100.0,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should have read from start_data
        assert result["tariff_name"] == "Pro"
        assert result["amount"] == 100.0

    async def test_dialog_data_takes_priority_over_start_data(
        self, mock_dialog_manager, mock_backend
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
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        mock_price_service = AsyncMock()
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=150.0,
            final_amount=150.0,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should use dialog_data (amount=150)
        assert result["tariff_name"] == "Dialog Tariff"
        assert result["amount"] == 150.0


# ---------------------------------------------------------------------------
# Full contract — KeyDetailsKeyboard → SettingsPayment
# ---------------------------------------------------------------------------


class TestRenewalStartDataContract:
    """Contract tests: KeyDetailsKeyboard → SettingsPayment start_data pattern."""

    async def test_start_data_from_key_details_matches_settings_payment_expectations(
        self, mock_dialog_manager, mock_backend
    ):
        """Start_data shape from KeyDetailsKeyboard matches SettingsPayment expectations."""
        key_data = make_key_dict("user@example.com", tariff_id=1)
        tariff_data = make_tariff_dict(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        mock_backend.get_key_details.return_value = key_data
        mock_backend.get_tariff.return_value = tariff_data

        # Step 1: KeyDetailsKeyboard writes start_data
        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_renewal_click(callback, button, mock_dialog_manager)

        start_data_passed: dict = mock_dialog_manager.start.call_args[1]["data"]

        # Step 2: SettingsPayment reads from start_data
        mock_dialog_manager.start_data = start_data_passed
        mock_dialog_manager.dialog_data = {}  # Simulate new dialog context
        mock_dialog_manager.event.answer = AsyncMock()

        getter = SettingsPayment(AsyncMock(), mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Verify all required fields are present
        assert result["tariff_name"] is not None
        assert "amount" in result
        assert "number_of_months" in result

    async def test_trial_start_data_contract(
        self, mock_dialog_manager, mock_backend
    ):
        """Trial renewal start_data contract: only email required."""
        mock_dialog_manager.dialog_data["email"] = "trial@example.com"

        keyboard = KeyDetailsKeyboard(mock_backend)
        callback = AsyncMock()
        button = MagicMock()
        await keyboard._on_trial_renewal_click(callback, button, mock_dialog_manager)

        # For trial renewal, only email is passed
        start_data = mock_dialog_manager.start.call_args[1]["data"]
        assert "email" in start_data
        assert start_data["email"] == "trial@example.com"
