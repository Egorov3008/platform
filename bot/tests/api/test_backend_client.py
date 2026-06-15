import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from api.backend_client import BackendAPIClient
from api.schemas import UserDTO, KeyDTO


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
async def test_get_user_returns_dto_on_200(client, mock_http):
    mock_http.get = AsyncMock(return_value=make_response(200, {
        "tg_id": 123, "username": "user", "first_name": "Test",
        "balance": 0.0, "trial": 0, "server_id": 2,
        "is_admin": False, "is_blocked": False,
    }))
    result = await client.get_user(123)
    assert result is not None
    assert isinstance(result, UserDTO)
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
    mock_http.get = AsyncMock(return_value=make_response(200, {
        "keys": [
            {
                "email": "user@vpn.ru", "tg_id": 123, "expiry_time": 9999999999000,
                "key": "https://sub.example.com/abc", "inbound_id": 11,
                "tariff_id": 9, "name_tariff": "Pro",
                "client_id": "abc-123",
                "total_gb": None, "used_traffic": 0.0,
            }
        ]
    }))
    result = await client.get_user_keys(123)
    assert len(result) == 1
    assert isinstance(result[0], KeyDTO)
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
    assert isinstance(result, UserDTO)
    assert result.tg_id == 456
    mock_http.post.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_returns_none_on_error(client, mock_http):
    mock_http.post = AsyncMock(side_effect=Exception("timeout"))
    result = await client.register_user(tg_id=456)
    assert result is None


# =============================================================================
# Regression: Referral stats endpoint returns the raw backend dict.
#
# The backend ``GET /api/v1/admin/referrals/stats/{tg_id}`` returns
# ``{"referral_count", "rewards_count", "rewards_total", "balance"}`` —
# the same shape consumed by ``dialogs/windows/getters/referral/main.py``
# and the referral message widget. Returning a typed DTO with mismatched
# field names (``referrer_tg_id``, ``total_referrals``, ...) was causing
# Pydantic validation errors that broke the entire referral window.
# =============================================================================

@pytest.mark.asyncio
async def test_get_referral_stats_returns_dict_on_200(client, mock_http):
    """Backend payload must come through unchanged as a dict.

    Regression test for the production error
    ``5 validation errors for ReferralStatsDTO`` — the typed DTO had
    field names that did not match the backend response.
    """
    payload = {
        "referral_count": 1,
        "rewards_count": 1,
        "rewards_total": 16.100000381469727,
        "balance": 0.0,
    }
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=payload)
    mock_http.request = AsyncMock(return_value=mock_response)

    result = await client.get_referral_stats(552810834)
    assert result == payload
    assert isinstance(result, dict)
    assert result["referral_count"] == 1
    assert result["rewards_total"] == 16.100000381469727
    mock_http.request.assert_called_once_with(
        "GET", "http://backend:8000/api/v1/admin/referrals/stats/552810834"
    )


@pytest.mark.asyncio
async def test_get_referral_stats_returns_none_on_error(client, mock_http):
    mock_http.request = AsyncMock(side_effect=Exception("connection refused"))
    result = await client.get_referral_stats(552810834)
    assert result is None


@pytest.mark.asyncio
async def test_get_referral_stats_returns_none_on_404(client, mock_http):
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
    )
    mock_http.request = AsyncMock(return_value=mock_response)
    result = await client.get_referral_stats(552810834)
    assert result is None
