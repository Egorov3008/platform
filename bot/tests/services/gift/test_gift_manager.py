"""
Тесты для GiftLinkProvider в services.core.gift.gift_manager.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from models import GiftLink
from services.core.gift.gift_manager import GiftLinkProvider


class TestGiftLinkProvider:
    @pytest.fixture
    def gift_gifts(self):
        """Мок для model_data.gifts (базовый репозиторий подарков)."""
        return AsyncMock()

    @pytest.fixture
    def gen_token(self, gift_gifts):
        from services.core.gift.repositories.gen_token import TokenGen

        model_data = AsyncMock()
        model_data.gifts = gift_gifts
        return TokenGen(model_data)

    @pytest.fixture
    def provider(self, gift_gifts, gen_token) -> GiftLinkProvider:
        model_data = AsyncMock()
        model_data.gifts = gift_gifts
        return GiftLinkProvider(gen_token, model_data)

    @pytest.mark.asyncio
    async def test_get_gift_link_existing(
        self, mock_conn, gift_gifts, gift_link, provider
    ):
        """Тест получения существующей ссылки на подарок."""
        gift_gifts.get_data = AsyncMock(return_value=gift_link)

        result = await provider.get_gift_link(user_id=123, conn=mock_conn, tariff_id=7)

        assert result == gift_link
        gift_gifts.get_data.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_gift_link_new(self, mock_conn, gift_gifts, gen_token, provider):
        """Тест создания новой ссылки на подарок."""
        gift_gifts.get_data = AsyncMock(return_value=None)
        gift_gifts.get_by = AsyncMock(return_value=None)
        gift_gifts.save_data = AsyncMock(return_value=True)
        token = "new_token_123"
        gen_token.create = AsyncMock(return_value=token)

        result = await provider.get_gift_link(user_id=123, conn=mock_conn, tariff_id=7)

        assert isinstance(result, GiftLink)
        assert result.sender_tg_id == 123
        assert result.tariff_id == 7
        assert result.token == token
        assert result._status == "active"

        gift_gifts.get_data.assert_called_once_with(123)
        gen_token.create.assert_called_once()
        gift_gifts.save_data.assert_called_once_with(
            mock_conn, result, sender_tg_id=123
        )

    @pytest.mark.asyncio
    async def test_application_success(
        self, mock_conn, gift_gifts, provider, gift_link
    ):
        """Тест успешного применения подарка."""
        gift = gift_link
        gift.sender_tg_id = 123
        gift_gifts.update = AsyncMock(return_value=True)

        recipient_id = 456
        email = "test@example.com"
        await provider.application(mock_conn, gift, recipient_id, email)

        assert gift.recipient_tg_id == recipient_id
        assert gift._status == "redeemed"
        gift_gifts.update.assert_called_once_with(
            mock_conn, gift, {"sender_tg_id": gift.sender_tg_id}
        )

    @pytest.mark.asyncio
    async def test_application_already_redeemed(
        self, mock_conn, gift_gifts, gift_link, provider
    ):
        """Тест попытки применения уже примененного подарка."""
        gift = gift_link
        gift.sender_tg_id = 123
        gift.redeem = Mock(side_effect=ValueError("Подарок недоступен для активации"))

        with pytest.raises(ValueError, match="Подарок недоступен для активации"):
            await provider.application(mock_conn, gift, 456, "test@example.com")

        gift.redeem.assert_called_once()
        gift_gifts.update.assert_not_called()
