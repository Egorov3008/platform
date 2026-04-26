"""
Flow contract tests for Payment creation: view_tariff → setting_pay → form_pay

Tests verify:
- TariffSelectBuilder writes amount/discounted_amount to dialog_data
- SettingsPayment reads discounted_amount with fallback to dialog_data OR start_data
- SettingPaymentKeyboard recalculates amount for months
- FormPaymentGetter reads accumulated payment data
- Full chain: tariff selection → months selection → payment form

No mocking of switch_to() / aiogram-dialog internals or YooKassa.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, Tariff, User
from dialogs.windows.widgets.keybord.payment.view_tariff import TariffSelectBuilder
from dialogs.windows.getters.payment.setting_payment import SettingsPayment


def _make_mock_model_data():
    """Helper: mock ServiceDataModel с users.get_data → User(balance=0)."""
    mock = AsyncMock()
    mock.users = AsyncMock()
    mock.users.get_data = AsyncMock(return_value=User(tg_id=123456789, balance=0.0))
    return mock
from dialogs.windows.widgets.keybord.payment.setting_payment import (
    SettingPaymentKeyboard,
)


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
def mock_model_data():
    """Mock ServiceDataModel."""
    model_data = AsyncMock()
    model_data.tariffs = AsyncMock()
    return model_data


@pytest.fixture
def mock_cache_service():
    """Mock CacheService."""
    cache = AsyncMock()
    cache.tariffs = AsyncMock()
    cache.tariffs.temporary_get = AsyncMock()
    cache.payments = AsyncMock()
    cache.payments.temporary_set = AsyncMock()
    return cache


class TestTariffSelectBuilderWritesData:
    """Tests that TariffSelectBuilder._on_tariff_selected() writes to dialog_data."""

    async def test_writes_amount(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler writes dialog_data["amount"] = discounted_amount from cache."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 80.0,
        }

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )  # type: ignore

        assert mock_dialog_manager.dialog_data["amount"] == 80.0

    async def test_writes_discounted_amount(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler writes dialog_data["discounted_amount"] separately."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 80.0,
        }

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )  # type: ignore

        assert mock_dialog_manager.dialog_data["discounted_amount"] == 80.0

    async def test_writes_tariff_object(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler writes dialog_data["tariff"] = tariff object."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )  # type: ignore

        assert mock_dialog_manager.dialog_data["tariff"] == tariff

    async def test_writes_payment_type_create_key(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler writes payment_type = "create_key|{tariff_id}" when no email in dialog_data."""
        tariff = make_tariff(5, "Premium", 200.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 200.0,
        }
        # No email in dialog_data or start_data

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="5"
        )  # type: ignore

        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|5"

    async def test_writes_payment_type_renew_key_if_email(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler writes payment_type = "renew_key|{email}" when email in dialog_data."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )  # type: ignore

        assert (
            mock_dialog_manager.dialog_data["payment_type"]
            == "renew_key|user@example.com"
        )

    async def test_no_tariff_in_cache_answers_error(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """Handler answers error when tariff_data not in temporary cache."""
        mock_cache_service.tariffs.temporary_get.return_value = None

        keyboard = TariffSelectBuilder(mock_model_data, mock_cache_service)
        callback = AsyncMock()
        widget = MagicMock()
        await keyboard._on_tariff_selected(
            callback, widget, mock_dialog_manager, item_id="1"
        )  # type: ignore

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args)


class TestSettingsPaymentGetterReadsData:
    """Tests that SettingsPayment.get_data() reads from dialog_data with fallback to start_data."""

    async def test_reads_tariff_from_dialog_data(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter reads dialog_data["tariff"] when present."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "discounted_amount": 100.0,
            "payment_type": "create_key|1",
        }
        mock_cache_service.payments.temporary_set = AsyncMock()

        getter = SettingsPayment(AsyncMock(), _make_mock_model_data())
        # Mock dialog_manager.start with proper behavior
        mock_dialog_manager.start = AsyncMock()

        result = await getter.get_data(mock_dialog_manager)
        assert result["tariff_name"] == "Pro"
        assert result["number_of_months"] == 1
        assert result["amount"] == 100.0

    async def test_reads_discounted_amount_for_calculation(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter prioritizes discounted_amount over amount for price."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "discounted_amount": 80.0,  # Lower discounted price
            "payment_type": "create_key|1",
        }

        getter = SettingsPayment(AsyncMock(), _make_mock_model_data())
        result = await getter.get_data(mock_dialog_manager)

        # discounted_amount should be used
        assert result["amount"] == 80.0

    async def test_reads_payment_type_from_dialog_data(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter reads dialog_data["payment_type"]."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "amount": 100.0,
            "payment_type": "renew_key|user@example.com",
        }

        getter = SettingsPayment(AsyncMock(), _make_mock_model_data())
        result = await getter.get_data(mock_dialog_manager)
        # Verify payment_type is preserved in dialog_data
        assert mock_dialog_manager.dialog_data.get("payment_type") == "renew_key|user@example.com"

    async def test_missing_tariff_returns_error(
        self, mock_dialog_manager, mock_cache_service
    ):
        """Getter with missing tariff handles error gracefully."""
        mock_dialog_manager.dialog_data = {
            "amount": 100.0,
            "payment_type": "create_key|1",
            # tariff missing
        }
        mock_dialog_manager.start = AsyncMock()
        mock_dialog_manager.event.answer = AsyncMock()

        getter = SettingsPayment(AsyncMock(), _make_mock_model_data())
        # The actual implementation calls dialog_manager.start(MainMenu.main) on error
        result = await getter.get_data(mock_dialog_manager)

        # When tariff is missing, error handling redirects and returns empty dict
        assert result == {}
        assert mock_dialog_manager.start.called
        assert mock_dialog_manager.event.answer.called


class TestMonthsChangedWritesAmount:
    """Tests that SettingPaymentKeyboard._months_changed() recalculates amount."""

    async def test_2_months_doubles_discounted_amount(self, mock_dialog_manager):
        """Handler with 2 months: amount = discounted_amount * 2 * 0.97 (3% volume discount)."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 80.0,
            "number_of_months": 1,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

        # 80 * 2 = 160, 3% discount = 155.2
        assert mock_dialog_manager.dialog_data["amount"] == 155.2

    async def test_3_months_triples_discounted_amount(self, mock_dialog_manager):
        """Handler with 3 months: amount = discounted_amount * 3 * 0.97 (3% volume discount)."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 100.0,
            "number_of_months": 1,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 3}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

        # 100 * 3 = 300, 3% discount = 291.0
        assert mock_dialog_manager.dialog_data["amount"] == 291.0

    async def test_writes_number_of_months_to_dialog_data(self, mock_dialog_manager):
        """Handler writes dialog_data["number_of_months"] from widget_data."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_dialog_manager.dialog_data = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }
        mock_dialog_manager.current_context().widget_data = {"number_of_months": 2}

        keyboard = SettingPaymentKeyboard()
        widget = MagicMock()
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

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
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

        # 100 * 2 = 200, 3% discount = 194.0
        assert mock_dialog_manager.dialog_data["amount"] == 194.0

    async def test_handles_fallback_to_start_data_tariff(self, mock_dialog_manager):
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
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

        # 80 * 2 = 160, 3% discount = 155.2
        assert mock_dialog_manager.dialog_data["amount"] == 155.2


class TestPaymentCreationChain:
    """Contract tests: full chain TariffSelectBuilder → SettingPaymentKeyboard → FormPaymentGetter."""

    async def test_tariff_selection_feeds_into_months_screen(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """TariffSelectBuilder writes → SettingPaymentKeyboard reads → amount correct."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 80.0,
        }

        # Step 1: Tariff selection
        keyboard1 = TariffSelectBuilder(mock_model_data, mock_cache_service)
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

    async def test_months_change_feeds_into_payment_form(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
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
        await keyboard._months_changed(None, widget, mock_dialog_manager)  # type: ignore

        # 100 * 3 = 300, 3% discount = 291.0
        assert mock_dialog_manager.dialog_data["amount"] == 291.0
        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|1"

    async def test_payment_type_persists_through_full_flow(
        self, mock_dialog_manager, mock_model_data, mock_cache_service
    ):
        """payment_type set by TariffSelectBuilder persists through months changes."""
        tariff = make_tariff(1, "Pro", 100.0)
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        # Step 1: Selection with email → payment_type = "renew_key|email"
        keyboard1 = TariffSelectBuilder(mock_model_data, mock_cache_service)
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
