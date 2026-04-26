"""
Tests for GiftGetter (MainGetter) - gift link URL generation.

GiftGetter.get_data() fetches user gift and generates shareable URL.
Side-effectful: requires mocking ServiceDataModel and GiftUrlGenerator.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from models import GiftLink
from dialogs.windows.getters.gift.main import MainGetter


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager"""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.gifts = AsyncMock()
    return model_data


@pytest.fixture
def mock_url_generator():
    """Mock GiftUrlGenerator"""
    return MagicMock()


@pytest.fixture
def sample_gift():
    """Sample GiftLink"""
    return GiftLink(sender_tg_id=123456789, tariff_id=1, token="gift_token_abc123")


class TestGiftGetterBasic:
    """Test GiftGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_gift_found(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should return gift link URL"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        mock_url_generator.generate.return_value = "https://t.me/bot?start=gift_abc123"

        getter = MainGetter(mock_model_data, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        assert "link" in result
        assert result["link"] == "https://t.me/bot?start=gift_abc123"

    @pytest.mark.asyncio
    async def test_get_data_calls_get_data_with_tg_id(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should call get_data with user tg_id"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        mock_url_generator.generate.return_value = "https://t.me/bot?start=token"

        getter = MainGetter(mock_model_data, mock_url_generator)
        await getter.get_data(mock_dialog_manager)

        mock_model_data.gifts.get_data.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_get_data_calls_generate_with_token(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should call generate with gift token"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        mock_url_generator.generate.return_value = (
            "https://t.me/bot?start=gift_token_abc123"
        )

        getter = MainGetter(mock_model_data, mock_url_generator)
        await getter.get_data(mock_dialog_manager)

        mock_url_generator.generate.assert_called_once_with("gift_token_abc123")


class TestGiftGetterURLGeneration:
    """Test GiftGetter URL generation"""

    @pytest.mark.asyncio
    async def test_get_data_returns_valid_url(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should return valid URL format"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        generated_url = "https://t.me/bot?start=gift_abc123"
        mock_url_generator.generate.return_value = generated_url

        getter = MainGetter(mock_model_data, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        url = result["link"]
        assert url.startswith("https://")
        assert "t.me" in url

    @pytest.mark.asyncio
    async def test_get_data_with_different_tokens(
        self, mock_model_data, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should generate different URLs for different tokens"""
        gift1 = GiftLink(sender_tg_id=111, tariff_id=1, token="token1")
        gift2 = GiftLink(sender_tg_id=222, tariff_id=2, token="token2")

        async def get_data_side_effect(tg_id):
            return gift1 if tg_id == 111 else gift2

        mock_model_data.gifts.get_data.side_effect = get_data_side_effect

        def generate_side_effect(token):
            return f"https://t.me/bot?start={token}"

        mock_url_generator.generate.side_effect = generate_side_effect

        getter = MainGetter(mock_model_data, mock_url_generator)

        manager1 = AsyncMock()
        manager1.event = MagicMock()
        manager1.event.from_user = MagicMock()
        manager1.event.from_user.id = 111

        manager2 = AsyncMock()
        manager2.event = MagicMock()
        manager2.event.from_user = MagicMock()
        manager2.event.from_user.id = 222

        result1 = await getter.get_data(manager1)
        result2 = await getter.get_data(manager2)

        assert "token1" in result1["link"]
        assert "token2" in result2["link"]
        assert result1["link"] != result2["link"]


class TestGiftGetterEdgeCases:
    """Test GiftGetter edge cases"""

    @pytest.mark.asyncio
    async def test_get_data_with_no_gift(
        self, mock_model_data, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should handle case when no gift returned"""
        mock_model_data.gifts.get_data.return_value = None

        getter = MainGetter(mock_model_data, mock_url_generator)

        # This will raise AttributeError when trying to access .token on None
        with pytest.raises(AttributeError):
            await getter.get_data(mock_dialog_manager)

    @pytest.mark.asyncio
    async def test_get_data_different_tariff_ids(
        self, mock_model_data, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should work with different tariff_ids"""
        gift1 = GiftLink(sender_tg_id=111, tariff_id=1, token="token1")
        gift2 = GiftLink(sender_tg_id=222, tariff_id=2, token="token2")
        gift3 = GiftLink(sender_tg_id=333, tariff_id=3, token="token3")

        gifts = [gift1, gift2, gift3]

        async def get_data_side_effect(tg_id):
            for gift in gifts:
                if gift.sender_tg_id == tg_id:
                    return gift
            return None

        mock_model_data.gifts.get_data.side_effect = get_data_side_effect
        mock_url_generator.generate.side_effect = lambda token: (
            f"https://t.me/bot?start={token}"
        )

        getter = MainGetter(mock_model_data, mock_url_generator)

        for tg_id, gift in zip([111, 222, 333], gifts):
            manager = AsyncMock()
            manager.event = MagicMock()
            manager.event.from_user = MagicMock()
            manager.event.from_user.id = tg_id

            result = await getter.get_data(manager)
            assert gift.token in result["link"]


class TestGiftGetterIntegration:
    """Integration tests for GiftGetter"""

    @pytest.mark.asyncio
    async def test_get_data_full_flow(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should handle complete gift URL generation flow"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        expected_url = "https://t.me/bot?start=gift_token_abc123"
        mock_url_generator.generate.return_value = expected_url

        getter = MainGetter(mock_model_data, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        # Verify result structure
        assert isinstance(result, dict)
        assert "link" in result

        # Verify calls were made in correct order
        mock_model_data.gifts.get_data.assert_called_once()
        mock_url_generator.generate.assert_called_once()

        # Verify the URL
        assert result["link"] == expected_url

    @pytest.mark.asyncio
    async def test_get_data_multiple_calls_same_user(
        self, mock_model_data, mock_url_generator, mock_dialog_manager, sample_gift
    ):
        """get_data() should work on multiple calls for same user"""
        mock_model_data.gifts.get_data.return_value = sample_gift
        mock_url_generator.generate.return_value = "https://t.me/bot?start=gift_abc123"

        getter = MainGetter(mock_model_data, mock_url_generator)

        result1 = await getter.get_data(mock_dialog_manager)
        result2 = await getter.get_data(mock_dialog_manager)

        assert result1["link"] == result2["link"]
        assert mock_model_data.gifts.get_data.call_count == 2
        assert mock_url_generator.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_get_data_with_different_users(
        self, mock_model_data, mock_url_generator
    ):
        """get_data() should fetch different gifts for different users"""
        gift1 = GiftLink(sender_tg_id=111, tariff_id=1, token="token_user1")
        gift2 = GiftLink(sender_tg_id=222, tariff_id=1, token="token_user2")

        async def get_data_side_effect(tg_id):
            return gift1 if tg_id == 111 else gift2

        mock_model_data.gifts.get_data.side_effect = get_data_side_effect
        mock_url_generator.generate.side_effect = lambda token: (
            f"https://t.me/bot?start={token}"
        )

        getter = MainGetter(mock_model_data, mock_url_generator)

        manager1 = AsyncMock()
        manager1.event = MagicMock()
        manager1.event.from_user = MagicMock()
        manager1.event.from_user.id = 111

        manager2 = AsyncMock()
        manager2.event = MagicMock()
        manager2.event.from_user = MagicMock()
        manager2.event.from_user.id = 222

        result1 = await getter.get_data(manager1)
        result2 = await getter.get_data(manager2)

        # Different tokens in URLs
        assert result1["link"] != result2["link"]
        assert "token_user1" in result1["link"]
        assert "token_user2" in result2["link"]
