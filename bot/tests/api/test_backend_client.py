import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from api.backend_client import BackendAPIClient, BackendUser, BackendKey


def make_mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_http():
    return make_mock_client()


@pytest.fixture
def client(mock_http):
    return BackendAPIClient(
        base_url="http://backend:8000",
        bot_secret="test-secret",
        client=mock_http,
    )


def make_response(status_code: int, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    if json_data is not None:
        r.json = MagicMock(return_value=json_data)
    r.raise_for_status = MagicMock()
    return r


@pytest.mark.asyncio
async def test_get_user_returns_user_on_200(client, mock_http):
    mock_http.get = AsyncMock(return_value=make_response(200, {
        "tg_id": 123, "username": "user", "first_name": "Test",
        "balance": 0.0, "trial": 0, "server_id": 2,
        "is_admin": False, "is_blocked": False,
    }))
    result = await client.get_user(123)
    assert result is not None
    assert isinstance(result, BackendUser)
    assert result.tg_id == 123
    assert result.username == "user"
    mock_http.get.assert_called_once_with("/api/v1/users/123")


@pytest.mark.asyncio
async def test_get_user_returns_none_on_404(client, mock_http):
    mock_http.get = AsyncMock(return_value=make_response(404))
    result = await client.get_user(999)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_returns_none_on_network_error(client, mock_http):
    mock_http.get = AsyncMock(side_effect=Exception("connection refused"))
    result = await client.get_user(123)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_keys_returns_list(client, mock_http):
    mock_http.get = AsyncMock(return_value=make_response(200, [
        {
            "email": "user@vpn.ru", "tg_id": 123, "expiry_time": 9999999999000,
            "key": "https://sub.example.com/abc", "inbound_id": 11,
            "tariff_id": 9, "name_tariff": "Pro",
            "total_gb": None, "used_traffic": 0.0,
        }
    ]))
    result = await client.get_user_keys(123)
    assert len(result) == 1
    assert isinstance(result[0], BackendKey)
    assert result[0].email == "user@vpn.ru"
    mock_http.get.assert_called_once_with("/api/v1/keys/", params={"tg_id": 123})


@pytest.mark.asyncio
async def test_get_user_keys_returns_empty_list_on_error(client, mock_http):
    mock_http.get = AsyncMock(side_effect=Exception("timeout"))
    result = await client.get_user_keys(123)
    assert result == []


@pytest.mark.asyncio
async def test_register_user_returns_user(client, mock_http):
    mock_http.post = AsyncMock(return_value=make_response(201, {
        "tg_id": 456, "username": "newuser", "first_name": "New",
        "balance": 0.0, "trial": 0, "server_id": 2,
        "is_admin": False, "is_blocked": False,
    }))
    result = await client.register_user(tg_id=456, username="newuser", first_name="New")
    assert result is not None
    assert result.tg_id == 456
    mock_http.post.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_returns_none_on_error(client, mock_http):
    mock_http.post = AsyncMock(side_effect=Exception("timeout"))
    result = await client.register_user(tg_id=456)
    assert result is None
