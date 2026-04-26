"""
Tests for CheckerGiftLink - gift link validation with mocks.

CheckerGiftLink.check() verifies if a user has a redeemable gift link.
Side-effectful: requires mocking ServiceDataModel.gifts.
"""

from unittest.mock import AsyncMock

import pytest

from models import GiftLink
from services.core.gift.repositories.checker import CheckerGiftLink


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.gifts = AsyncMock()
    return model_data


@pytest.fixture
def valid_gift_link():
    """Valid, redeemable gift link"""
    return GiftLink(
        sender_tg_id=111,
        tariff_id=1,
        token="gift_token_valid",
        # _status defaults to "active", so is_redeemable() returns True
    )


@pytest.fixture
def redeemed_gift_link():
    """Redeemed gift link (not redeemable)"""
    gift = GiftLink(
        sender_tg_id=111,
        tariff_id=1,
        token="gift_token_redeemed",
        recipient_tg_id=222,  # Once recipient_tg_id is set, _status becomes "redeemed"
        email="recipient@example.com",
    )
    return gift


class TestCheckerGiftLinkBasic:
    """Test basic CheckerGiftLink.check() functionality"""

    @pytest.mark.asyncio
    async def test_check_gift_found_redeemable(self, mock_model_data, valid_gift_link):
        """check() should return True for valid gift link"""
        # valid_gift_link has _status="active", so is_redeemable() returns True
        mock_model_data.gifts.get_data.return_value = valid_gift_link

        checker = CheckerGiftLink(mock_model_data)
        result = await checker.check(123456789)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_gift_not_found(self, mock_model_data):
        """check() should return False when gift not found"""
        mock_model_data.gifts.get_data.return_value = None

        checker = CheckerGiftLink(mock_model_data)
        result = await checker.check(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_gift_not_redeemable(self, mock_model_data):
        """check() should return False when gift not redeemable"""
        gift = GiftLink(sender_tg_id=111, tariff_id=1, token="token")
        gift.is_redeemable = lambda: False
        mock_model_data.gifts.get_data.return_value = gift

        checker = CheckerGiftLink(mock_model_data)
        result = await checker.check(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_calls_get_data_with_user_id(
        self, mock_model_data, valid_gift_link
    ):
        """check() should call get_data with user_id"""
        valid_gift_link.is_redeemable = lambda: True
        mock_model_data.gifts.get_data.return_value = valid_gift_link

        checker = CheckerGiftLink(mock_model_data)
        await checker.check(123456789)

        mock_model_data.gifts.get_data.assert_called_once_with(123456789)


class TestCheckerGiftLinkEdgeCases:
    """Test edge cases for CheckerGiftLink"""

    @pytest.mark.asyncio
    async def test_check_gift_is_redeemable_throws(self, mock_model_data):
        """check() should handle exception from is_redeemable()"""
        gift = GiftLink(sender_tg_id=111, tariff_id=1, token="token")
        gift.is_redeemable = lambda: (_ for _ in ()).throw(Exception("Check error"))
        mock_model_data.gifts.get_data.return_value = gift

        checker = CheckerGiftLink(mock_model_data)

        # This will raise because is_redeemable() throws
        with pytest.raises(Exception):
            await checker.check(123456789)

    @pytest.mark.asyncio
    async def test_check_get_data_throws(self, mock_model_data):
        """check() should propagate exception from get_data()"""
        mock_model_data.gifts.get_data.side_effect = Exception("DB error")

        checker = CheckerGiftLink(mock_model_data)

        with pytest.raises(Exception, match="DB error"):
            await checker.check(123456789)

    @pytest.mark.asyncio
    async def test_check_multiple_calls_same_user(
        self, mock_model_data, valid_gift_link
    ):
        """check() should work correctly on multiple calls"""
        valid_gift_link.is_redeemable = lambda: True
        mock_model_data.gifts.get_data.return_value = valid_gift_link

        checker = CheckerGiftLink(mock_model_data)

        result1 = await checker.check(123456789)
        result2 = await checker.check(123456789)

        assert result1 == result2 == True
        assert mock_model_data.gifts.get_data.call_count == 2

    @pytest.mark.asyncio
    async def test_check_different_users(self, mock_model_data):
        """check() should handle different user IDs"""
        gift1 = GiftLink(sender_tg_id=111, tariff_id=1, token="token1")
        gift1.is_redeemable = lambda: True
        gift2 = GiftLink(sender_tg_id=222, tariff_id=2, token="token2")
        gift2.is_redeemable = lambda: False

        async def side_effect(user_id):
            if user_id == 111:
                return gift1
            elif user_id == 222:
                return gift2
            return None

        mock_model_data.gifts.get_data.side_effect = side_effect

        checker = CheckerGiftLink(mock_model_data)

        result1 = await checker.check(111)
        result2 = await checker.check(222)
        result3 = await checker.check(999)

        assert result1 is True
        assert result2 is False
        assert result3 is False


class TestCheckerGiftLinkIntegration:
    """Integration tests for CheckerGiftLink"""

    @pytest.mark.asyncio
    async def test_check_respects_gift_validity(self, mock_model_data):
        """check() should respect is_redeemable() logic"""
        # Create a real GiftLink with active status
        gift_valid = GiftLink(
            sender_tg_id=111,
            tariff_id=1,
            token="valid_token",
            # Default _status is "active", so is_redeemable() returns True
        )

        mock_model_data.gifts.get_data.return_value = gift_valid

        checker = CheckerGiftLink(mock_model_data)
        result = await checker.check(123456789)

        # Should be redeemable (_status is "active")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_multiple_instances(self, mock_model_data, valid_gift_link):
        """Multiple CheckerGiftLink instances should work independently"""
        # valid_gift_link is already redeemable (active status)
        mock_model_data.gifts.get_data.return_value = valid_gift_link

        checker1 = CheckerGiftLink(mock_model_data)
        checker2 = CheckerGiftLink(mock_model_data)

        result1 = await checker1.check(123456789)
        result2 = await checker2.check(123456789)

        assert result1 == result2 == True
