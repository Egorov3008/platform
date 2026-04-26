"""
Tests for TariffSelectBuilder (dialogs/windows/widgets/keybord/payment/view_tariff.py).

Tests verify:
- _on_tariff_selected() saves tariff_id to cache for renewal
- Cache key pattern: renewal_tariff_{email}
- TTL is set correctly (15 minutes)
- Fallback behavior when tariff_data is missing
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Tariff
from dialogs.windows.widgets.keybord.payment.view_tariff import TariffSelectBuilder
from states.payment import PaymentState


@pytest.fixture
def mock_model_service():
    """Mock ServiceDataModel."""
    model_service = AsyncMock()
    model_service.tariffs = AsyncMock()
    return model_service


@pytest.fixture
def mock_cache_service():
    """Mock CacheService with tariffs namespace."""
    cache_service = AsyncMock()
    cache_service.tariffs = AsyncMock()
    cache_service.tariffs.temporary_get = AsyncMock()
    cache_service.tariffs.temporary_set = AsyncMock()
    return cache_service


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

    async def test_saves_tariff_id_to_cache_for_renewal(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected saves tariff_id to cache when email is present."""
        tariff = make_tariff(1, "Pro", 100.0)
        
        # Setup: tariff data in cache
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 90.0,
        }
        
        # Setup: email in dialog_data (renewal flow)
        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )
        
        # Verify cache was called with correct key and TTL
        mock_cache_service.tariffs.temporary_set.assert_called_once()
        call_args = mock_cache_service.tariffs.temporary_set.call_args
        
        # Check key pattern
        assert call_args[0][0] == "renewal_tariff_user@example.com"
        
        # Check TTL
        assert call_args[1]["ttl"] == timedelta(minutes=15)
        
        # Check tariff_id saved
        assert call_args[1]["tariff_id"] == 1

    async def test_saves_correct_tariff_id_from_item_id(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected saves the selected item_id as tariff_id."""
        tariff = make_tariff(5, "Premium", 500.0)
        
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 450.0,
        }
        
        mock_dialog_manager.dialog_data["email"] = "user@example.com"
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="5"
        )
        
        call_args = mock_cache_service.tariffs.temporary_set.call_args
        assert call_args[1]["tariff_id"] == 5

    async def test_no_cache_save_without_email(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected does not save to cache when email is missing."""
        tariff = make_tariff(1, "Pro", 100.0)
        
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 90.0,
        }
        
        # No email in dialog_data or start_data (creation flow)
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {}
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )
        
        # temporary_set should not be called for renewal cache
        # (it might be called for other purposes, but not renewal_tariff_*)
        calls = mock_cache_service.tariffs.temporary_set.call_args_list
        renewal_calls = [
            c for c in calls 
            if len(c[0]) > 0 and str(c[0][0]).startswith("renewal_tariff_")
        ]
        assert len(renewal_calls) == 0

    async def test_email_from_start_data(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected reads email from start_data when dialog_data empty."""
        tariff = make_tariff(2, "Standard", 200.0)
        
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 180.0,
        }
        
        # Email in start_data
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {"email": "trial@example.com"}
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="2"
        )
        
        call_args = mock_cache_service.tariffs.temporary_set.call_args
        assert call_args[0][0] == "renewal_tariff_trial@example.com"
        assert call_args[1]["tariff_id"] == 2

    async def test_dialog_data_email_takes_priority(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected prefers email from dialog_data over start_data."""
        tariff = make_tariff(3, "Enterprise", 1000.0)
        
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 900.0,
        }
        
        # Email in both dialog_data and start_data
        mock_dialog_manager.dialog_data = {"email": "dialog@example.com"}
        mock_dialog_manager.start_data = {"email": "start@example.com"}
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="3"
        )
        
        call_args = mock_cache_service.tariffs.temporary_set.call_args
        # Should use email from dialog_data
        assert call_args[0][0] == "renewal_tariff_dialog@example.com"

    async def test_switches_to_setting_pay_after_selection(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected switches to PaymentState.setting_pay."""
        from aiogram_dialog.api.entities import ShowMode
        
        tariff = make_tariff(1, "Pro", 100.0)

        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 90.0,
        }

        mock_dialog_manager.dialog_data["email"] = "user@example.com"

        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        mock_dialog_manager.switch_to.assert_called_once_with(
            PaymentState.setting_pay,
            show_mode=ShowMode.EDIT
        )

    async def test_missing_tariff_data_answers_error(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected answers error when tariff data not found."""
        mock_cache_service.tariffs.temporary_get.return_value = None
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="999"
        )
        
        mock_callback.answer.assert_called_once()
        assert "❌" in str(mock_callback.answer.call_args)
        
        # Cache should not be called
        mock_cache_service.tariffs.temporary_set.assert_not_called()
        
        # Should not switch to setting_pay
        mock_dialog_manager.switch_to.assert_not_called()

    async def test_cache_save_with_dict_tariff_data(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected correctly handles dict tariff_data with discount."""
        tariff = make_tariff(4, "Business", 300.0)
        discounted_amount = 250.0
        
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": discounted_amount,
        }
        
        mock_dialog_manager.dialog_data["email"] = "business@example.com"
        
        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)
        
        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="4"
        )
        
        # Verify cache save was called
        mock_cache_service.tariffs.temporary_set.assert_called()
        
        # Verify dialog_data was updated with discounted amount
        assert mock_dialog_manager.dialog_data["amount"] == discounted_amount
        assert mock_dialog_manager.dialog_data["tariff"] == tariff

    async def test_cache_save_with_legacy_tariff_direct(
        self, mock_model_service, mock_cache_service, mock_dialog_manager,
        mock_callback, mock_widget
    ):
        """_on_tariff_selected handles legacy format (tariff directly, not dict)."""
        tariff = make_tariff(1, "Pro", 100.0)

        # Legacy format: tariff directly, not in dict
        mock_cache_service.tariffs.temporary_get.return_value = {
            "tariff": tariff,
            "discounted_amount": 100.0,
        }

        mock_dialog_manager.dialog_data["email"] = "legacy@example.com"

        builder = TariffSelectBuilder(mock_model_service, mock_cache_service)

        await builder._on_tariff_selected(
            mock_callback, mock_widget, mock_dialog_manager, item_id="1"
        )

        # Should still save to cache
        mock_cache_service.tariffs.temporary_set.assert_called()
        call_args = mock_cache_service.tariffs.temporary_set.call_args
        assert call_args[0][0] == "renewal_tariff_legacy@example.com"
        assert call_args[1]["tariff_id"] == 1
