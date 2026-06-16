"""
Flow contract tests for Payment creation: view_tariff → setting_pay → form_pay

Source: dialogs/windows/widgets/keybord/payment/view_tariff.py
        dialogs/windows/getters/payment/setting_payment.py
        dialogs/windows/widgets/keybord/payment/setting_payment.py

Contract:
- TariffSelectBuilder._on_tariff_selected writes amount/tariff/payment_type to
  dialog_data, reading tariff from ``processed_tariffs[item_id]`` (set by
  TariffPreviewGetter).
- SettingsPayment.get_data reads those fields, applies volume discount (3% for
  2-6 months, from config.DISCOUNTS) and optional referral discount from
  backend.get_user(tg_id)["balance"].
- SettingPaymentKeyboard._months_changed recalculates amount when the
  Counter widget changes its value.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, Tariff
from dialogs.windows.widgets.keybord.payment.view_tariff import TariffSelectBuilder
from dialogs.windows.getters.payment.setting_payment import SettingsPayment


def make_tariff(tariff_id: int = 1, name: str = "Pro", amount: float = 100.0) -> Tariff:
    """Helper to create a test Tariff."""
    return Tariff(
        id=tariff_id,
        name_tariff=name,
        amount=amount,
    )


def make_key(
    email: str, tg_id: int = 123456789, expiry_offset_ms: int = 86400000
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
        tariff_id=1,
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
    manager.current_context = MagicMock()
    manager.current_context().widget_data = {"number_of_months": 1}
    return manager


@pytest.fixture
def mock_price_service():
    """Mock PriceCalculatorProtocol — calculate(tg_id, tariff) → PriceResult."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.get_user = AsyncMock(return_value=None)
    return backend


# ---------------------------------------------------------------------------
# TariffSelectBuilder — writes to dialog_data
# ---------------------------------------------------------------------------


class TestTariffSelectBuilderWritesData:
    """Tests that TariffSelectBuilder._on_tariff_selected() writes to dialog_data."""

    async def test_writes_amount(self, mock_dialog_manager):
        """Handler writes dialog_data["amount"] = discounted_amount from processed_tariffs."""
        tariff = make_tariff(1, "Pro", 100.0)
        # Source reads from ``processed_tariffs[item_id]`` (dict with "tariff"
        # and "discounted_amount" keys, set by TariffPreviewGetter).
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 80.0}
        }

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["amount"] == 80.0

    async def test_writes_discounted_amount(self, mock_dialog_manager):
        """Handler writes dialog_data["discounted_amount"] separately."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 80.0}
        }

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["discounted_amount"] == 80.0

    async def test_writes_tariff_object(self, mock_dialog_manager):
        """Handler writes dialog_data["tariff"] = tariff object."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 100.0}
        }

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["tariff"] == tariff

    async def test_writes_payment_type_create_key(self, mock_dialog_manager):
        """Handler writes payment_type = "create_key|{tariff_id}" when no email."""
        tariff = make_tariff(5, "Premium", 200.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "5": {"tariff": tariff, "discounted_amount": 200.0}
        }

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="5"
        )

        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|5"

    async def test_writes_payment_type_renew_key_if_email(self, mock_dialog_manager):
        """Handler writes payment_type = "renew_key|{email}" when email present."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 100.0}
        }
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        assert (
            mock_dialog_manager.dialog_data["payment_type"]
            == "renew_key|user@example.com"
        )

    async def test_no_tariff_in_processed_answers_error(self, mock_dialog_manager):
        """Handler answers error when tariff_data not in processed_tariffs."""
        # No processed_tariffs in dialog_data
        mock_dialog_manager.dialog_data = {}

        keyboard = TariffSelectBuilder()
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)


# ---------------------------------------------------------------------------
# SettingsPayment.get_data — reads data
# ---------------------------------------------------------------------------


class TestSettingsPaymentGetterReadsData:
    """Tests that SettingsPayment.get_data() reads from dialog_data."""

    async def test_reads_tariff_from_dialog_data(
        self, mock_dialog_manager, mock_price_service, mock_backend
    ):
        """Getter reads dialog_data["tariff"] when present."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "discounted_amount": 100.0,
            "payment_type": "create_key|1",
        }
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Pro"
        assert result["number_of_months"] == 1
        assert result["amount"] == 100.0

    async def test_reads_discounted_amount_for_calculation(
        self, mock_dialog_manager, mock_price_service, mock_backend
    ):
        """Getter prioritizes discounted_amount over amount for price."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "discounted_amount": 80.0,  # Stock-discounted
            "payment_type": "create_key|1",
        }
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # When number_of_months == 1, no volume discount, no referral discount
        # so the amount equals the per-month discounted price (80.0).
        assert result["amount"] == 80.0

    async def test_reads_payment_type_from_dialog_data(
        self, mock_dialog_manager, mock_price_service, mock_backend
    ):
        """Getter reads dialog_data["payment_type"] and persists it."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "payment_type": "renew_key|user@example.com",
        }
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        await getter.get_data(mock_dialog_manager)

        # Verify payment_type is preserved in dialog_data after the call
        assert mock_dialog_manager.dialog_data.get("payment_type") == "renew_key|user@example.com"

    async def test_missing_tariff_returns_error(
        self, mock_dialog_manager, mock_price_service, mock_backend
    ):
        """Getter with missing tariff handles error gracefully (returns empty dict)."""
        mock_dialog_manager.dialog_data = {
            "amount": 100.0,
            "payment_type": "create_key|1",
            # tariff missing
        }
        mock_dialog_manager.event.answer = AsyncMock()
        mock_dialog_manager.start = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # When tariff is missing, error handling redirects and returns empty dict
        assert result == {}
        assert mock_dialog_manager.start.called
        assert mock_dialog_manager.event.answer.called


# ---------------------------------------------------------------------------
# SettingPaymentKeyboard — recalculates amount on months change
# ---------------------------------------------------------------------------


from dialogs.windows.widgets.keybord.payment.setting_payment import (
    SettingPaymentKeyboard,
)


class TestMonthsChangedWritesAmount:
    """Tests that SettingPaymentKeyboard._months_changed() recalculates amount."""

    async def test_2_months_applies_volume_discount(self, mock_dialog_manager):
        """With 2 months, amount = discounted_amount * 2 * 0.97 (3% volume discount)."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 80.0,
            "number_of_months": 1,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        # 80 * 2 = 160, 3% discount = 155.2
        assert mock_dialog_manager.dialog_data["amount"] == 155.2

    async def test_3_months_applies_volume_discount(self, mock_dialog_manager):
        """With 3 months, amount = discounted_amount * 3 * 0.97 (3% volume discount)."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 100.0,
            "number_of_months": 1,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 3}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        # 100 * 3 = 300, 3% discount = 291.0
        assert mock_dialog_manager.dialog_data["amount"] == 291.0

    async def test_writes_number_of_months_to_dialog_data(
        self, mock_dialog_manager
    ):
        """Handler writes dialog_data["number_of_months"] from widget_data."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["number_of_months"] == 2

    async def test_uses_original_tariff_amount_when_no_discount(
        self, mock_dialog_manager
    ):
        """Handler uses tariff.amount when discounted_amount absent."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            # discounted_amount is absent
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        # 100 * 2 = 200, 3% discount = 194.0
        assert mock_dialog_manager.dialog_data["amount"] == 194.0

    async def test_handles_fallback_to_start_data_tariff(
        self, mock_dialog_manager
    ):
        """Handler reads tariff from start_data when dialog_data["tariff"] absent."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            # No tariff in dialog_data
            "discounted_amount": 80.0,
        }
        mock_dialog_manager.start_data = {
            "tariff": tariff,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        # 80 * 2 = 160, 3% discount = 155.2
        assert mock_dialog_manager.dialog_data["amount"] == 155.2


# ---------------------------------------------------------------------------
# Full chain — TariffSelectBuilder → SettingPaymentKeyboard
# ---------------------------------------------------------------------------


class TestPaymentCreationChain:
    """Contract tests: full chain TariffSelectBuilder → SettingPaymentKeyboard."""

    async def test_tariff_selection_feeds_into_months_screen(
        self, mock_dialog_manager
    ):
        """TariffSelectBuilder writes → SettingPaymentKeyboard reads → amount correct."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 80.0}
        }

        # Step 1: Tariff selection
        keyboard1 = TariffSelectBuilder()
        callback = AsyncMock()
        await keyboard1._on_tariff_selected(
            callback, None, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["discounted_amount"] == 80.0
        assert mock_dialog_manager.dialog_data["amount"] == 80.0

        # Step 2: Months changed (with 3% volume discount)
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}
        keyboard2 = SettingPaymentKeyboard()
        await keyboard2._months_changed(None, None, mock_dialog_manager)

        # 80 * 2 = 160, 3% discount = 155.2
        assert mock_dialog_manager.dialog_data["amount"] == 155.2

    async def test_months_change_preserves_payment_type(
        self, mock_dialog_manager
    ):
        """Amount updates from months changes are available for payment form."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 100.0,
            "payment_type": "create_key|1",
        }

        # Simulate months change (with 3% volume discount)
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 3}
        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)

        # 100 * 3 = 300, 3% discount = 291.0
        assert mock_dialog_manager.dialog_data["amount"] == 291.0
        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|1"

    async def test_payment_type_persists_through_full_flow(
        self, mock_dialog_manager
    ):
        """payment_type set by TariffSelectBuilder persists through months changes."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 100.0}
        }
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        # Step 1: Selection with email → payment_type = "renew_key|email"
        keyboard1 = TariffSelectBuilder()
        callback = AsyncMock()
        await keyboard1._on_tariff_selected(
            callback, None, mock_dialog_manager, item_id="1"
        )

        initial_payment_type = mock_dialog_manager.dialog_data["payment_type"]
        assert initial_payment_type == "renew_key|user@example.com"

        # Step 2: Months change should NOT modify payment_type
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}
        keyboard2 = SettingPaymentKeyboard()
        await keyboard2._months_changed(None, None, mock_dialog_manager)

        # payment_type should be unchanged
        assert mock_dialog_manager.dialog_data["payment_type"] == initial_payment_type
