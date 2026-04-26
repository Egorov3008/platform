"""
Тесты для ReferralLinkGenerator.
"""
from unittest.mock import AsyncMock, patch

import pytest

from models import ReferralLink
from services.core.referral.link_generator import ReferralLinkGenerator
from services.core.data.service import ServiceDataModel


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=ServiceDataModel)
    service.referral_links = AsyncMock()
    return service


@pytest.fixture
def link_generator(mock_service):
    gen = ReferralLinkGenerator(mock_service)
    gen._referral_data = mock_service.referral_links
    return gen


@pytest.fixture
def mock_pool():
    return AsyncMock()


class TestGetOrCreate:
    async def test_returns_existing_link(self, link_generator, mock_service, mock_pool):
        existing = ReferralLink(referrer_tg_id=123, token="ref_existing", id=1)
        mock_service.referral_links.get_by = AsyncMock(return_value=existing)

        result = await link_generator.get_or_create(mock_pool, 123)

        assert result.token == "ref_existing"
        mock_service.referral_links.save_data.assert_not_called()

    async def test_creates_new_link_when_none_exists(
        self, link_generator, mock_service, mock_pool
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=None)
        mock_service.referral_links.save_data = AsyncMock()

        result = await link_generator.get_or_create(mock_pool, 456)

        assert result.referrer_tg_id == 456
        assert result.token.startswith("ref_")
        mock_service.referral_links.save_data.assert_called_once()

    async def test_new_link_token_is_unique_format(
        self, link_generator, mock_service, mock_pool
    ):
        mock_service.referral_links.get_by = AsyncMock(return_value=None)
        mock_service.referral_links.save_data = AsyncMock()

        result = await link_generator.get_or_create(mock_pool, 789)

        assert result.token.startswith("ref_")
        assert len(result.token) == 16  # "ref_" + 12 hex chars


class TestGetShareUrl:
    @patch("services.core.referral.link_generator.BOT_NAME", "test_bot")
    def test_share_url_format(self, link_generator):
        url = link_generator.get_share_url("ref_abc123")

        assert url == "https://t.me/test_bot?start=ref_abc123"


class TestGenerateToken:
    def test_token_starts_with_ref_prefix(self):
        token = ReferralLinkGenerator._generate_token()

        assert token.startswith("ref_")

    def test_token_has_correct_length(self):
        token = ReferralLinkGenerator._generate_token()

        assert len(token) == 16  # "ref_" (4) + 12 hex

    def test_tokens_are_unique(self):
        tokens = {ReferralLinkGenerator._generate_token() for _ in range(100)}

        assert len(tokens) == 100
