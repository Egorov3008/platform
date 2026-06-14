"""
Tests for TariffSelectBuilder (dialogs/windows/widgets/keybord/payment/view_tariff.py).

Tests verify:
- _on_tariff_selected() saves email to dialog_data for backend to use
- tariff_id is passed correctly via payment_type
- Fallback behavior when tariff_data is missing
- Email priority: dialog_data over start_data

Note: Cache saving is now handled by backend at POST /payments/create,
not by the bot. The bot only stores email in dialog_data.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Tariff
from dialogs.windows.widgets.keybord.payment.view_tariff import TariffSelectBuilder
from states.payment import PaymentState


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data, start_data, and event."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    manager.start_data = {}
    manager.switch_to = AsyncMock()
    return manager


@pytest.fixture
def mock_callback():
    """Mock CallbackQuery."""
    callback = AsyncMock()
    return callback


@pytest.fixture
def mock_widget():
    """Mock Select widget."""
    widget = MagicMock()
    return widget


def make_tariff(tariff_id: int = 1, name: str = "Pro", amount: float = 100.0) -> Tariff:
    """Helper to create a test Tariff."""
    return Tariff(
        id=tariff_id,
        name_tariff=name,
        amount=amount,
    )


class TestTariffSelectBuilderRenewal:
    """Tests for tariff selection with renewal flow."""

    async def test_saves_email_to_dialog_data_for_renewal(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected saves email to dialog_data for backend to use."""
        tariff = make_tariff(1, "Pro", 100.0)

        # Setup: tariff data in processed_tariffs (from TariffPreviewGetter)
        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 90.0}
        }

        # Setup: email in dialog_data (renewal flow)
        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        # Verify email is preserved in dialog_data (backend will use it)
        assert mock_dialog_manager.dialog_data["email"] == "user@example.com"

        # Verify payment_type was set correctly
        assert mock_dialog_manager.dialog_data["payment_type"] == "renew_key|user@example.com"

    async def test_saves_correct_tariff_id_in_payment_type(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected includes correct tariff_id in payment_type."""
        tariff = make_tariff(5, "Premium", 500.0)

        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "5": {"tariff": tariff, "discounted_amount": 450.0}
        }

        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="5"
        )

        # payment_type contains tariff_id from item_id for create_key
        # For renew_key, tariff_id will be read by backend from request body
        assert "renew_key|user@example.com" in mock_dialog_manager.dialog_data["payment_type"]

    async def test_no_email_for_creation_flow(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected uses create_key flow when email is missing."""
        tariff = make_tariff(1, "Pro", 100.0)

        # No email (creation flow) - keep processed_tariffs but no email
        mock_dialog_manager.dialog_data = {"processed_tariffs": {"1": {"tariff": tariff, "discounted_amount": 90.0}}}
        mock_dialog_manager.start_data = {}

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        # Should use create_key flow with tariff_id
        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|1"

    async def test_email_from_start_data(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected reads email from start_data when dialog_data empty."""
        tariff = make_tariff(2, "Standard", 200.0)

        # processed_tariffs in dialog_data, email in start_data
        mock_dialog_manager.dialog_data = {"processed_tariffs": {"2": {"tariff": tariff, "discounted_amount": 180.0}}}
        mock_dialog_manager.start_data = {"email": "trial@example.com"}

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="2"
        )

        # Email should be saved to dialog_data
        assert mock_dialog_manager.dialog_data["email"] == "trial@example.com"
        assert mock_dialog_manager.dialog_data["payment_type"] == "renew_key|trial@example.com"

    async def test_dialog_data_email_takes_priority(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected prefers email from dialog_data over start_data."""
        tariff = make_tariff(3, "Enterprise", 1000.0)

        # Email in both dialog_data and start_data - dialog_data wins
        mock_dialog_manager.dialog_data = {
            "processed_tariffs": {"3": {"tariff": tariff, "discounted_amount": 900.0}},
            "email": "dialog@example.com"
        }
        mock_dialog_manager.start_data = {"email": "start@example.com"}

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="3"
        )

        # Should use email from dialog_data
        assert mock_dialog_manager.dialog_data["email"] == "dialog@example.com"
        assert mock_dialog_manager.dialog_data["payment_type"] == "renew_key|dialog@example.com"

    async def test_switches_to_setting_pay_after_selection(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected switches to PaymentState.setting_pay."""
        from aiogram_dialog.api.entities import ShowMode

        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 90.0}
        }

        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        mock_dialog_manager.switch_to.assert_called_once_with(
            PaymentState.setting_pay,
            show_mode=ShowMode.EDIT
        )

    async def test_missing_tariff_data_answers_error(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected answers error when tariff data not found."""
        # No processed_tariffs - tariff data not found
        mock_dialog_manager.dialog_data = {}

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="999"
        )

        mock_callback.answer.assert_called_once()
        assert "❌" in str(mock_callback.answer.call_args)

        # Should not switch to setting_pay
        mock_dialog_manager.switch_to.assert_not_called()

    async def test_dialog_data_updated_with_discount(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected correctly handles dict tariff_data with discount."""
        tariff = make_tariff(4, "Business", 300.0)
        discounted_amount = 250.0

        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "4": {"tariff": tariff, "discounted_amount": discounted_amount}
        }

        mock_dialog_manager.dialog_data["email"] = "business@example.com"

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="4"
        )

        # Verify dialog_data was updated with discounted amount
        assert mock_dialog_manager.dialog_data["amount"] == discounted_amount
        assert mock_dialog_manager.dialog_data["tariff"] == tariff

    async def test_legacy_tariff_format(
        self, mock_dialog_manager, mock_callback, mock_widget
    ):
        """_on_tariff_selected handles legacy format (tariff directly, not dict)."""
        tariff = make_tariff(1, "Pro", 100.0)

        mock_dialog_manager.dialog_data["processed_tariffs"] = {
            "1": {"tariff": tariff, "discounted_amount": 100.0}
        }

        mock_dialog_manager.dialog_data["email"] = "legacy@example.com"

        builder = TariffSelectBuilder()

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        assert mock_dialog_manager.dialog_data["email"] == "legacy@example.com"
        assert mock_dialog_manager.dialog_data["amount"] == 100.0
