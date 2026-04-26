from unittest.mock import AsyncMock

import pytest

from models import User, Key


@pytest.mark.asyncio
async def test_ensure_user_exists_new(key_creator, mock_model_data):  # noqa: PT019, PT006
    """Тест создания нового пользователя."""
    mock_model_data.users.get_data.return_value = None

    result = await key_creator.ensure_user_exists(12345)

    assert result is True
    mock_model_data.users.save_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_user_exists_existing(key_creator, mock_model_data):  # noqa: PT019, PT006
    """Тест существующего пользователя."""
    mock_model_data.users.get_data.return_value = User(tg_id=12345)

    result = await key_creator.ensure_user_exists(12345)

    assert result is True
    mock_model_data.users.save_data.assert_not_called()


@pytest.mark.asyncio
async def test_create_key_success(key_creator, mock_model_data, mock_tariff_matcher, sample_client):  # noqa: PT019, PT006
    """Тест успешного создания ключа."""
    server = mock_model_data.servers.get.return_value = type(
        "Server", (), {"subscription_url": "https://test-server.com"}
    )()
    mock_tariff_matcher.match.return_value = 10

    result = await key_creator.create_key(sample_client)

    assert isinstance(result, Key)
    assert result.email == "test@example.com"
    assert result.tariff_id == 10
    mock_model_data.keys.save_data.assert_awaited_once()
    mock_tariff_matcher.match.assert_awaited_once_with(sample_client)


@pytest.mark.asyncio
async def test_create_key_no_server(key_creator, mock_model_data, sample_client):  # noqa: PT019, PT006
    """Тест создания ключа без сервера."""
    mock_model_data.servers.get_data.return_value = None

    result = await key_creator.create_key(sample_client)

    assert result is None
