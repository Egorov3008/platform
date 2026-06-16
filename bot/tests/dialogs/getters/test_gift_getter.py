"""
Tests for MainGetter (gift link URL generation).

MainGetter.get_data() fetches user's gifts via BackendAPIClient.admin_list_gifts()
and generates shareable URL via GiftUrlGenerator.

Source: dialogs/windows/getters/gift/main.py
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dialogs.windows.getters.gift.main import MainGetter


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with from_user.id."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.admin_list_gifts = AsyncMock(return_value=[])
    return backend


@pytest.fixture
def mock_url_generator():
    """Mock GiftUrlGenerator."""
    return MagicMock()


def make_gift_dict(token: str, sender_tg_id: int = 123456789, tariff_id: int = 1) -> dict:
    """Build a backend-shaped dict for a gift."""
    return {
        "sender_tg_id": sender_tg_id,
        "tariff_id": tariff_id,
        "token": token,
    }


# ---------------------------------------------------------------------------
# MainGetter — базовая функциональность
# ---------------------------------------------------------------------------


class TestGiftGetterBasic:
    """Test MainGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_gift_found(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should return gift link URL when gift exists."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("gift_token_abc123")]
        mock_url_generator.generate.return_value = "https://t.me/bot?start=gift_abc123"

        getter = MainGetter(mock_backend, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        assert "link" in result
        assert result["link"] == "https://t.me/bot?start=gift_abc123"

    @pytest.mark.asyncio
    async def test_get_data_calls_admin_list_gifts_with_tg_id(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should call admin_list_gifts with user tg_id."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("token")]
        mock_url_generator.generate.return_value = "https://t.me/bot?start=token"

        getter = MainGetter(mock_backend, mock_url_generator)
        await getter.get_data(mock_dialog_manager)

        mock_backend.admin_list_gifts.assert_called_once_with(sender_tg_id=123456789)

    @pytest.mark.asyncio
    async def test_get_data_calls_generate_with_token(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should call generate with gift token."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("gift_token_abc123")]
        mock_url_generator.generate.return_value = "https://t.me/bot?start=token"

        getter = MainGetter(mock_backend, mock_url_generator)
        await getter.get_data(mock_dialog_manager)

        mock_url_generator.generate.assert_called_once_with("gift_token_abc123")


# ---------------------------------------------------------------------------
# MainGetter — генерация URL
# ---------------------------------------------------------------------------


class TestGiftGetterURLGeneration:
    """Test MainGetter URL generation"""

    @pytest.mark.asyncio
    async def test_get_data_returns_valid_url(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should return valid URL format."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("gift_abc123")]
        generated_url = "https://t.me/bot?start=gift_abc123"
        mock_url_generator.generate.return_value = generated_url

        getter = MainGetter(mock_backend, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        url = result["link"]
        assert url.startswith("https://")
        assert "t.me" in url

    @pytest.mark.asyncio
    async def test_get_data_with_different_tokens(
        self, mock_backend, mock_url_generator
    ):
        """get_data() should generate different URLs for different tokens."""
        gift_map = {
            111: make_gift_dict("token1", sender_tg_id=111),
            222: make_gift_dict("token2", sender_tg_id=222),
        }

        async def list_gifts_side_effect(sender_tg_id):
            gift = gift_map.get(sender_tg_id)
            return [gift] if gift else []

        mock_backend.admin_list_gifts.side_effect = list_gifts_side_effect
        mock_url_generator.generate.side_effect = lambda token: (
            f"https://t.me/bot?start={token}"
        )

        getter = MainGetter(mock_backend, mock_url_generator)

        def make_manager(tg_id: int):
            m = AsyncMock()
            m.event = MagicMock()
            m.event.from_user = MagicMock()
            m.event.from_user.id = tg_id
            return m

        result1 = await getter.get_data(make_manager(111))
        result2 = await getter.get_data(make_manager(222))

        assert "token1" in result1["link"]
        assert "token2" in result2["link"]
        assert result1["link"] != result2["link"]


# ---------------------------------------------------------------------------
# MainGetter — граничные случаи
# ---------------------------------------------------------------------------


class TestGiftGetterEdgeCases:
    """Test MainGetter edge cases"""

    @pytest.mark.asyncio
    async def test_get_data_with_no_gift(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """When no gifts exist, get_data() returns empty link and does not call generate."""
        mock_backend.admin_list_gifts.return_value = []

        getter = MainGetter(mock_backend, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        assert result["link"] == ""
        mock_url_generator.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_data_different_tariff_ids(
        self, mock_backend, mock_url_generator
    ):
        """get_data() should work with different tariff_ids."""
        gift_map = {
            111: make_gift_dict("token1", sender_tg_id=111, tariff_id=1),
            222: make_gift_dict("token2", sender_tg_id=222, tariff_id=2),
            333: make_gift_dict("token3", sender_tg_id=333, tariff_id=3),
        }

        async def list_gifts_side_effect(sender_tg_id):
            gift = gift_map.get(sender_tg_id)
            return [gift] if gift else []

        mock_backend.admin_list_gifts.side_effect = list_gifts_side_effect
        mock_url_generator.generate.side_effect = lambda token: (
            f"https://t.me/bot?start={token}"
        )

        getter = MainGetter(mock_backend, mock_url_generator)

        def make_manager(tg_id: int):
            m = AsyncMock()
            m.event = MagicMock()
            m.event.from_user = MagicMock()
            m.event.from_user.id = tg_id
            return m

        for tg_id, gift in gift_map.items():
            result = await getter.get_data(make_manager(tg_id))
            assert gift["token"] in result["link"]


# ---------------------------------------------------------------------------
# MainGetter — интеграционные сценарии
# ---------------------------------------------------------------------------


class TestGiftGetterIntegration:
    """Integration tests for MainGetter"""

    @pytest.mark.asyncio
    async def test_get_data_full_flow(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should handle complete gift URL generation flow."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("gift_token_abc123")]
        expected_url = "https://t.me/bot?start=gift_token_abc123"
        mock_url_generator.generate.return_value = expected_url

        getter = MainGetter(mock_backend, mock_url_generator)
        result = await getter.get_data(mock_dialog_manager)

        # Verify result structure
        assert isinstance(result, dict)
        assert "link" in result

        # Verify calls were made in correct order
        mock_backend.admin_list_gifts.assert_called_once()
        mock_url_generator.generate.assert_called_once()

        # Verify the URL
        assert result["link"] == expected_url

    @pytest.mark.asyncio
    async def test_get_data_multiple_calls_same_user(
        self, mock_backend, mock_url_generator, mock_dialog_manager
    ):
        """get_data() should work on multiple calls for same user."""
        mock_backend.admin_list_gifts.return_value = [make_gift_dict("gift_abc123")]
        mock_url_generator.generate.return_value = "https://t.me/bot?start=gift_abc123"

        getter = MainGetter(mock_backend, mock_url_generator)

        result1 = await getter.get_data(mock_dialog_manager)
        result2 = await getter.get_data(mock_dialog_manager)

        assert result1["link"] == result2["link"]
        assert mock_backend.admin_list_gifts.call_count == 2
        assert mock_url_generator.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_get_data_with_different_users(
        self, mock_backend, mock_url_generator
    ):
        """get_data() should fetch different gifts for different users."""
        gift_map = {
            111: make_gift_dict("token_user1", sender_tg_id=111),
            222: make_gift_dict("token_user2", sender_tg_id=222),
        }

        async def list_gifts_side_effect(sender_tg_id):
            gift = gift_map.get(sender_tg_id)
            return [gift] if gift else []

        mock_backend.admin_list_gifts.side_effect = list_gifts_side_effect
        mock_url_generator.generate.side_effect = lambda token: (
            f"https://t.me/bot?start={token}"
        )

        getter = MainGetter(mock_backend, mock_url_generator)

        def make_manager(tg_id: int):
            m = AsyncMock()
            m.event = MagicMock()
            m.event.from_user = MagicMock()
            m.event.from_user.id = tg_id
            return m

        result1 = await getter.get_data(make_manager(111))
        result2 = await getter.get_data(make_manager(222))

        # Different tokens in URLs
        assert result1["link"] != result2["link"]
        assert "token_user1" in result1["link"]
        assert "token_user2" in result2["link"]
