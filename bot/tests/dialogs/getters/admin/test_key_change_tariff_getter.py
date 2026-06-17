"""
Tests for AdminKeyChangeTariffGetter and AdminKeyChangeTariffConfirmGetter.

These getters load tariff lists from the backend API (which returns dicts).
The keyboard widget formats them with `item[1].name_tariff`, so the items
must be Tariff objects (with attribute access), not dicts.

Regression test: bot-1 logs showed
'AttributeError: dict object has no attribute name_tariff' on the
change_tariff flow.
"""

from unittest.mock import AsyncMock

import pytest

from models import Tariff
from dialogs.windows.getters.admin.key_actions import (
    AdminKeyChangeTariffGetter,
    AdminKeyChangeTariffConfirmGetter,
)


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_backend():
    return AsyncMock()


# ---------------------------------------------------------------------------
# AdminKeyChangeTariffGetter
# ---------------------------------------------------------------------------


class TestAdminKeyChangeTariffGetterTariffObjects:
    """tariff_list items must be Tariff objects, not dicts."""

    async def test_tariff_list_items_are_tariff_objects(
        self, mock_backend, mock_dialog_manager
    ):
        """Items in tariff_list must expose name_tariff as an attribute."""
        mock_dialog_manager.start_data = {"email": "user@example.com"}
        mock_backend.get_key_details.return_value = {"email": "user@example.com"}
        mock_backend.admin_list_tariffs.return_value = [
            {"id": 1, "name_tariff": "Basic", "amount": 500, "traffic_limit": 100},
            {"id": 2, "name_tariff": "Pro", "amount": 900, "traffic_limit": 500},
        ]

        getter = AdminKeyChangeTariffGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "tariff_list" in result
        assert len(result["tariff_list"]) == 2
        for _item_id, item in result["tariff_list"]:
            assert isinstance(item, Tariff), (
                f"Expected Tariff, got {type(item).__name__} — "
                "Format('item[1].name_tariff') requires attribute access"
            )
            # Attribute access must work — used by Format template
            assert item.name_tariff in ("Basic", "Pro")
            assert item.amount in (500, 900)

    async def test_tariff_list_id_is_string(
        self, mock_backend, mock_dialog_manager
    ):
        """item_id_getter=lambda x: str(x[0]) — id must be string."""
        mock_dialog_manager.start_data = {"email": "user@example.com"}
        mock_backend.get_key_details.return_value = {"email": "user@example.com"}
        mock_backend.admin_list_tariffs.return_value = [
            {"id": 42, "name_tariff": "X", "amount": 1},
        ]

        getter = AdminKeyChangeTariffGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        item_id, _ = result["tariff_list"][0]
        assert item_id == "42"

    async def test_returns_empty_on_no_email(
        self, mock_backend, mock_dialog_manager
    ):
        mock_backend.get_key_details.return_value = None
        mock_backend.admin_list_tariffs.return_value = []

        getter = AdminKeyChangeTariffGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result == {"email": "", "tariff_list": []}


# ---------------------------------------------------------------------------
# AdminKeyChangeTariffConfirmGetter
# ---------------------------------------------------------------------------


class TestAdminKeyChangeTariffConfirmGetterTariffObject:
    """get_tariff result should be normalized too if used as an object."""

    async def test_tariff_name_read_from_dict(
        self, mock_backend, mock_dialog_manager
    ):
        """get_tariff returns a dict, getter reads tariff_name via .get()."""
        mock_dialog_manager.start_data = {"email": "user@example.com"}
        mock_dialog_manager.dialog_data = {"selected_tariff_id": 7}
        mock_backend.get_key_details.return_value = {"email": "user@example.com"}
        mock_backend.get_tariff.return_value = {
            "id": 7,
            "name_tariff": "Premium",
            "traffic_limit": 1000,
            "amount": 1500,
        }

        getter = AdminKeyChangeTariffConfirmGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["email"] == "user@example.com"
        assert result["tariff_name"] == "Premium"

    async def test_returns_empty_when_tariff_missing(
        self, mock_backend, mock_dialog_manager
    ):
        mock_dialog_manager.start_data = {"email": "user@example.com"}
        mock_dialog_manager.dialog_data = {"selected_tariff_id": 7}
        mock_backend.get_key_details.return_value = {"email": "user@example.com"}
        mock_backend.get_tariff.return_value = None

        getter = AdminKeyChangeTariffConfirmGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result == {"email": "", "tariff_name": ""}
