import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.backend_client import WebBackendClient


@pytest.fixture
def mock_http_client():
    """Create a mock httpx.AsyncClient."""
    return AsyncMock()


@pytest.fixture
def backend_client(mock_http_client):
    """Create a WebBackendClient with mock HTTP client."""
    return WebBackendClient(
        http_client=mock_http_client,
        tg_id=12345,
        bot_secret="test-secret",
    )


@pytest.fixture
def backend_client_no_auth(mock_http_client):
    """Create a WebBackendClient without tg_id (public endpoints)."""
    return WebBackendClient(
        http_client=mock_http_client,
        tg_id=None,
        bot_secret="test-secret",
    )


@pytest.mark.asyncio
async def test_list_tariffs(backend_client_no_auth, mock_http_client):
    """Test list_tariffs returns list of tariffs."""
    expected_tariffs = [
        {"id": 1, "name": "Basic", "amount": 100},
        {"id": 2, "name": "Pro", "amount": 200},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = expected_tariffs
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client_no_auth.list_tariffs()

    assert result == expected_tariffs
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/tariffs/" in call_args[0]
    assert call_args[1]["headers"]["X-Bot-Secret"] == "test-secret"


@pytest.mark.asyncio
async def test_get_tariff(backend_client_no_auth, mock_http_client):
    """Test get_tariff returns specific tariff."""
    expected_tariff = {"id": 1, "name": "Basic", "amount": 100}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_tariff
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client_no_auth.get_tariff(1)

    assert result == expected_tariff
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/tariffs/1" in call_args[0]


@pytest.mark.asyncio
async def test_list_keys_empty(backend_client, mock_http_client):
    """Test list_keys returns empty list when user has no keys."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.list_keys()

    assert result == []
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/keys" in call_args[0]
    assert call_args[1]["params"]["tg_id"] == 12345


@pytest.mark.asyncio
async def test_list_keys_multiple(backend_client, mock_http_client):
    """Test list_keys returns multiple keys."""
    expected_keys = [
        {"email": "user1@example.com", "tariff_id": 1},
        {"email": "user2@example.com", "tariff_id": 2},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = expected_keys
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.list_keys()

    assert result == expected_keys
    assert len(result) == 2


@pytest.mark.asyncio
async def test_create_key(backend_client, mock_http_client):
    """Test create_key returns new key details."""
    expected_key = {"email": "newuser@example.com", "tariff_id": 1, "expires_at": "2024-05-27"}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_key
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response

    result = await backend_client.create_key(1)

    assert result == expected_key
    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert "/api/v1/keys/create" in call_args[0]
    assert call_args[1]["json"]["tariff_id"] == 1
    assert call_args[1]["params"]["tg_id"] == 12345


@pytest.mark.asyncio
async def test_delete_key(backend_client, mock_http_client):
    """Test delete_key handles 204 No Content response."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_response.raise_for_status = MagicMock()
    mock_http_client.delete.return_value = mock_response

    result = await backend_client.delete_key("user@example.com")

    assert result is None
    mock_http_client.delete.assert_called_once()
    call_args = mock_http_client.delete.call_args
    assert "/api/v1/keys/user@example.com" in call_args[0]


@pytest.mark.asyncio
async def test_renew_key(backend_client, mock_http_client):
    """Test renew_key returns updated key details."""
    expected_key = {"email": "user@example.com", "tariff_id": 2, "expires_at": "2024-09-27"}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_key
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response

    result = await backend_client.renew_key("user@example.com", 2, 4)

    assert result == expected_key
    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert "/api/v1/keys/user@example.com/renew" in call_args[0]
    assert call_args[1]["json"]["tariff_id"] == 2
    assert call_args[1]["json"]["months"] == 4


@pytest.mark.asyncio
async def test_get_payment_history_empty(backend_client, mock_http_client):
    """Test get_payment_history returns empty list when no payments."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.get_payment_history()

    assert result == []
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/payments" in call_args[0]
    assert call_args[1]["params"]["tg_id"] == 12345


@pytest.mark.asyncio
async def test_get_payment_history_multiple(backend_client, mock_http_client):
    """Test get_payment_history returns multiple payments."""
    expected_payments = [
        {"payment_id": "pay1", "amount": 100, "status": "succeeded"},
        {"payment_id": "pay2", "amount": 200, "status": "succeeded"},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = expected_payments
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.get_payment_history()

    assert result == expected_payments
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_payment_status_success(backend_client, mock_http_client):
    """Test get_payment_status returns payment details."""
    expected_payment = {"payment_id": "pay1", "status": "succeeded", "amount": 100}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_payment
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.get_payment_status("pay1")

    assert result == expected_payment
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/payments/pay1/status" in call_args[0]


@pytest.mark.asyncio
async def test_get_payment_status_pending(backend_client, mock_http_client):
    """Test get_payment_status with pending status."""
    expected_payment = {"payment_id": "pay1", "status": "pending", "amount": 100}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_payment
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.get_payment_status("pay1")

    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_get_user(backend_client, mock_http_client):
    """Test get_user returns user details."""
    expected_user = {"tg_id": 12345, "username": "testuser"}
    mock_response = MagicMock()
    mock_response.json.return_value = expected_user
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await backend_client.get_user(12345)

    assert result == expected_user
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "/api/v1/users/12345" in call_args[0]


@pytest.mark.asyncio
async def test_headers_include_bot_secret(backend_client, mock_http_client):
    """Test that all requests include X-Bot-Secret header."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await backend_client.list_keys()

    call_args = mock_http_client.get.call_args
    assert call_args[1]["headers"]["X-Bot-Secret"] == "test-secret"


@pytest.mark.asyncio
async def test_params_include_tg_id_when_authenticated(backend_client, mock_http_client):
    """Test that tg_id is included in params for authenticated client."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await backend_client.list_keys()

    call_args = mock_http_client.get.call_args
    assert call_args[1]["params"]["tg_id"] == 12345


@pytest.mark.asyncio
async def test_params_exclude_tg_id_when_not_authenticated(backend_client_no_auth, mock_http_client):
    """Test that tg_id is not included in params for unauthenticated client."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await backend_client_no_auth.list_tariffs()

    call_args = mock_http_client.get.call_args
    assert call_args[1] == {"headers": {"X-Bot-Secret": "test-secret"}}


@pytest.mark.asyncio
async def test_create_payment(backend_client, mock_http_client):
    """Test create_payment returns payment details."""
    expected_payment = {
        "payment_id": "pay123",
        "amount": 500,
        "tariff_id": 1,
        "months": 1,
    }
    mock_response = MagicMock()
    mock_response.json.return_value = expected_payment
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response

    result = await backend_client.create_payment(1, 1)

    assert result == expected_payment
    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert "/api/v1/payments/create" in call_args[0]
    assert call_args[1]["json"]["tariff_id"] == 1
    assert call_args[1]["json"]["months"] == 1
