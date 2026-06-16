"""
Tests for CheckerGiftLink - gift link validation with mocks.

CheckerGiftLink.check() verifies if a user has a redeemable gift link.
Side-effectful: requires mocking BackendAPIClient.admin_list_gifts().
"""

from unittest.mock import AsyncMock

import pytest

from services.core.gift.repositories.checker import CheckerGiftLink


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient with admin_list_gifts."""
    backend = AsyncMock()
    backend.admin_list_gifts = AsyncMock(return_value=[])
    return backend


class TestCheckerGiftLinkBasic:
    """Test basic CheckerGiftLink.check() functionality"""

    @pytest.mark.asyncio
    async def test_check_gift_found_redeemable(self, mock_backend):
        """check() should return True when an active gift exists."""
        # No redeemed_at / recipient_tg_id → still redeemable.
        mock_backend.admin_list_gifts.return_value = [
            {
                "token": "gift_token_valid",
                "sender_tg_id": 111,
                "tariff_id": 1,
            }
        ]

        checker = CheckerGiftLink(mock_backend)
        result = await checker.check(123456789)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_gift_not_found(self, mock_backend):
        """check() should return False when no gifts exist."""
        mock_backend.admin_list_gifts.return_value = []

        checker = CheckerGiftLink(mock_backend)
        result = await checker.check(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_gift_not_redeemable(self, mock_backend):
        """check() should return False when all gifts are already redeemed."""
        # Both fields populated → fully redeemed.
        mock_backend.admin_list_gifts.return_value = [
            {
                "token": "token",
                "sender_tg_id": 111,
                "tariff_id": 1,
                "redeemed_at": "2026-06-10T10:00:00Z",
                "recipient_tg_id": 222,
            }
        ]

        checker = CheckerGiftLink(mock_backend)
        result = await checker.check(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_calls_admin_list_gifts_with_user_id(self, mock_backend):
        """check() should call admin_list_gifts with sender_tg_id=user_id."""
        mock_backend.admin_list_gifts.return_value = [
            {"token": "t", "sender_tg_id": 111, "tariff_id": 1}
        ]

        checker = CheckerGiftLink(mock_backend)
        await checker.check(123456789)

        mock_backend.admin_list_gifts.assert_called_once_with(
            sender_tg_id=123456789
        )


class TestCheckerGiftLinkEdgeCases:
    """Test edge cases for CheckerGiftLink"""

    @pytest.mark.asyncio
    async def test_check_admin_list_gifts_throws(self, mock_backend):
        """check() should propagate exception from admin_list_gifts()."""
        mock_backend.admin_list_gifts.side_effect = Exception("Backend error")

        checker = CheckerGiftLink(mock_backend)

        with pytest.raises(Exception, match="Backend error"):
            await checker.check(123456789)

    @pytest.mark.asyncio
    async def test_check_only_redeemed_gifts(self, mock_backend):
        """All gifts redeemed → False."""
        mock_backend.admin_list_gifts.return_value = [
            {
                "token": "t1",
                "sender_tg_id": 111,
                "tariff_id": 1,
                "redeemed_at": "2026-06-01",
                "recipient_tg_id": 333,
            },
            {
                "token": "t2",
                "sender_tg_id": 111,
                "tariff_id": 1,
                "used_at": "2026-06-02",
                "used_by_tg_id": 444,
            },
        ]

        checker = CheckerGiftLink(mock_backend)
        result = await checker.check(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_multiple_calls_same_user(self, mock_backend):
        """check() should be idempotent for the same user."""
        mock_backend.admin_list_gifts.return_value = [
            {"token": "t", "sender_tg_id": 111, "tariff_id": 1}
        ]

        checker = CheckerGiftLink(mock_backend)

        result1 = await checker.check(123456789)
        result2 = await checker.check(123456789)

        assert result1 is True
        assert result2 is True
        assert mock_backend.admin_list_gifts.call_count == 2

    @pytest.mark.asyncio
    async def test_check_different_users(self, mock_backend):
        """check() should pass the right user_id to admin_list_gifts."""
        async def side_effect(sender_tg_id=None):
            if sender_tg_id == 111:
                return [{"token": "t1", "sender_tg_id": 111, "tariff_id": 1}]
            if sender_tg_id == 222:
                return [
                    {
                        "token": "t2",
                        "sender_tg_id": 222,
                        "tariff_id": 2,
                        "redeemed_at": "2026-06-01",
                        "recipient_tg_id": 333,
                    }
                ]
            return []

        mock_backend.admin_list_gifts.side_effect = side_effect

        checker = CheckerGiftLink(mock_backend)

        assert await checker.check(111) is True
        assert await checker.check(222) is False
        assert await checker.check(999) is False


class TestCheckerGiftLinkIntegration:
    """Integration tests for CheckerGiftLink"""

    @pytest.mark.asyncio
    async def test_check_respects_gift_validity(self, mock_backend):
        """Mixed list: one active gift → True."""
        mock_backend.admin_list_gifts.return_value = [
            {
                "token": "used",
                "sender_tg_id": 111,
                "tariff_id": 1,
                "redeemed_at": "2026-06-01",
                "recipient_tg_id": 333,
            },
            {
                "token": "valid",
                "sender_tg_id": 111,
                "tariff_id": 1,
            },
        ]

        checker = CheckerGiftLink(mock_backend)
        result = await checker.check(123456789)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_multiple_instances(self, mock_backend):
        """Multiple CheckerGiftLink instances share the same backend mock."""
        mock_backend.admin_list_gifts.return_value = [
            {"token": "t", "sender_tg_id": 111, "tariff_id": 1}
        ]

        checker1 = CheckerGiftLink(mock_backend)
        checker2 = CheckerGiftLink(mock_backend)

        result1 = await checker1.check(123456789)
        result2 = await checker2.check(123456789)

        assert result1 is True
        assert result2 is True
