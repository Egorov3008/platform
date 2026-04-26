"""
Comprehensive async tests for GiftRegistration.

Covers: can_handle (valid/invalid/expired gifts), register() success/failure.
"""
from unittest.mock import AsyncMock

import pytest

from models import GiftLink
from registration.gift_registration import GiftRegistration
from services.core.data.service import ServiceDataModel


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=ServiceDataModel)
    service.gifts = AsyncMock()
    return service


@pytest.fixture
def gift_registration(mock_service):
    reg = GiftRegistration(mock_service)
    reg._gift_data = mock_service.gifts
    return reg


@pytest.fixture
def active_gift():
    return GiftLink(sender_tg_id=100, tariff_id=3, token="active_token_001")


@pytest.fixture
def redeemed_gift():
    # recipient_tg_id triggers _status="redeemed" in __post_init__
    return GiftLink(
        sender_tg_id=100,
        tariff_id=3,
        token="used_token_001",
        recipient_tg_id=200,
    )


class TestGiftRegistrationCanHandle:
    async def test_can_handle_valid_gift_token_returns_true(
        self, gift_registration, mock_service, active_gift
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=active_gift)

        result = await gift_registration.can_handle("active_token_001")

        mock_service.gifts.get_by.assert_called_once_with(token="active_token_001")
        assert result is True

    async def test_can_handle_invalid_gift_token_not_found_returns_false(
        self, gift_registration, mock_service
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=None)

        result = await gift_registration.can_handle("nonexistent_token")

        mock_service.gifts.get_by.assert_called_once_with(token="nonexistent_token")
        assert result is False

    async def test_can_handle_redeemed_gift_returns_false(
        self, gift_registration, mock_service, redeemed_gift
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=redeemed_gift)

        result = await gift_registration.can_handle("used_token_001")

        assert result is False

    async def test_can_handle_expired_gift_via_manual_status(
        self, gift_registration, mock_service, active_gift
    ):
        """Manually set _status to something other than 'active' → not redeemable."""
        active_gift._status = "expired"
        mock_service.gifts.get_by = AsyncMock(return_value=active_gift)

        result = await gift_registration.can_handle("active_token_001")

        assert result is False

    async def test_can_handle_calls_gift_data_with_correct_token(
        self, gift_registration, mock_service
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=None)
        token = "check_token_xyz"

        await gift_registration.can_handle(token)

        mock_service.gifts.get_by.assert_called_once_with(token=token)


class TestGiftRegistrationRegister:
    async def test_register_gift_returns_correct_data(
        self, gift_registration, mock_service, active_gift
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=active_gift)

        result = await gift_registration.register("active_token_001")

        assert result == {
            "success": True,
            "type": "gift",
            "token": "active_token_001",
            "tariff_id": active_gift.tariff_id,
            "from_user_id": active_gift.sender_tg_id,
        }

    async def test_register_includes_tariff_id_from_gift_link(
        self, gift_registration, mock_service
    ):
        gift = GiftLink(sender_tg_id=777, tariff_id=5, token="token_tariff5")
        mock_service.gifts.get_by = AsyncMock(return_value=gift)

        result = await gift_registration.register("token_tariff5")

        assert result["tariff_id"] == 5

    async def test_register_includes_sender_tg_id(
        self, gift_registration, mock_service
    ):
        gift = GiftLink(sender_tg_id=888888, tariff_id=1, token="t")
        mock_service.gifts.get_by = AsyncMock(return_value=gift)

        result = await gift_registration.register("t")

        assert result["from_user_id"] == 888888

    async def test_register_returns_failure_when_gift_not_found(
        self, gift_registration, mock_service
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=None)

        result = await gift_registration.register("missing_token")

        assert result == {"success": False, "error": "gift_link_not_found"}

    async def test_register_queries_gift_data_by_token(
        self, gift_registration, mock_service, active_gift
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=active_gift)

        await gift_registration.register("active_token_001")

        mock_service.gifts.get_by.assert_called_once_with(token="active_token_001")

    async def test_register_success_type_is_gift(
        self, gift_registration, mock_service, active_gift
    ):
        mock_service.gifts.get_by = AsyncMock(return_value=active_gift)

        result = await gift_registration.register("active_token_001")

        assert result["type"] == "gift"
        assert result["success"] is True
