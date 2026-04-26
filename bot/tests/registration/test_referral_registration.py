"""
Тесты для ReferralRegistration.

Covers: can_handle (valid/invalid links), register() success/failure.
"""
from unittest.mock import AsyncMock

import pytest

from models import ReferralLink
from registration.referral_registration import ReferralRegistration
from services.core.data.service import ServiceDataModel


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=ServiceDataModel)
    service.referral_links = AsyncMock()
    return service


@pytest.fixture
def referral_registration(mock_service):
    reg = ReferralRegistration(mock_service)
    reg._referral_data = mock_service.referral_links
    return reg


@pytest.fixture
def active_link():
    return ReferralLink(referrer_tg_id=100, token="ref_abc123", id=1)


class TestReferralRegistrationCanHandle:
    async def test_can_handle_valid_token_returns_true(
        self, referral_registration, mock_service, active_link
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=active_link)

        result = await referral_registration.can_handle("ref_abc123")

        mock_service.referral_links.get_by.assert_called_once_with(token="ref_abc123")
        assert result is True

    async def test_can_handle_invalid_token_returns_false(
        self, referral_registration, mock_service
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=None)

        result = await referral_registration.can_handle("nonexistent")

        assert result is False

    async def test_can_handle_queries_by_token(
        self, referral_registration, mock_service
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=None)
        token = "ref_xyz789"

        await referral_registration.can_handle(token)

        mock_service.referral_links.get_by.assert_called_once_with(token=token)


class TestReferralRegistrationRegister:
    async def test_register_returns_correct_data(
        self, referral_registration, mock_service, active_link
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=active_link)

        result = await referral_registration.register("ref_abc123")

        assert result == {
            "success": True,
            "type": "referral",
            "token": "ref_abc123",
            "referrer_tg_id": 100,
            "referral_link_id": 1,
        }

    async def test_register_returns_failure_when_link_not_found(
        self, referral_registration, mock_service
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=None)

        result = await referral_registration.register("missing")

        assert result == {"success": False, "error": "referral_link_not_found"}

    async def test_register_type_is_referral(
        self, referral_registration, mock_service, active_link
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=active_link)

        result = await referral_registration.register("ref_abc123")

        assert result["type"] == "referral"
        assert result["success"] is True

    async def test_register_includes_referrer_tg_id(
        self, referral_registration, mock_service
    ):
        link = ReferralLink(referrer_tg_id=999, token="ref_t1", id=5)
        mock_service.referral_links.get_by = AsyncMock(return_value=link)

        result = await referral_registration.register("ref_t1")

        assert result["referrer_tg_id"] == 999
        assert result["referral_link_id"] == 5
