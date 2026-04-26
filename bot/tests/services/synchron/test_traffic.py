from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_fetch_traffic_batch_success(
    traffic_updater, mock_http_session, sample_client
):  # noqa: PT019, PT006
    """Тест успешного получения трафика для пакета."""
    # Настройка мока ответа
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"upload": 1000, "download": 2000}

    mock_http_session.get.return_value.__aenter__.return_value = mock_response

    result = await traffic_updater.fetch_traffic_batch(
        [sample_client], "https://test-server.com", mock_http_session
    )

    assert "test@example.com" in result
    assert result["test@example.com"]["upload"] == 1000


@pytest.mark.asyncio
async def test_fetch_traffic_batch_404(
    traffic_updater, mock_http_session, sample_client
):  # noqa: PT019, PT006
    """Тест обработки 404 статуса."""
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_http_session.get.return_value.__aenter__.return_value = mock_response

    result = await traffic_updater.fetch_traffic_batch(
        [sample_client], "https://test-server.com", mock_http_session
    )

    assert result["test@example.com"] is None


@pytest.mark.asyncio
async def test_fetch_traffic_batch_non_json(
    traffic_updater, mock_http_session, sample_client
):  # noqa: PT019, PT006
    """Тест обработки не-JSON ответа."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.text.return_value = "Plain text"

    mock_http_session.get.return_value.__aenter__.return_value = mock_response

    result = await traffic_updater.fetch_traffic_batch(
        [sample_client], "https://test-server.com", mock_http_session
    )

    assert "content_type" in result["test@example.com"]
    assert result["test@example.com"]["text"] == "Plain text"


@pytest.mark.asyncio
async def test_parse_traffic_info_success(traffic_updater):  # noqa: PT019, PT006
    """Тест успешного парсинга информации о трафике."""
    response_data = {
        "headers": {"Subscription-Userinfo": "upload=1000; download=2000; total=10000"}
    }

    result = await traffic_updater.parse_traffic_info(response_data)

    assert result["upload_bytes"] == 1000
    assert result["download_bytes"] == 2000
    assert result["used_bytes"] == 3000
    assert result["total_bytes"] == 10000
    assert result["usage_percent"] == 30.0


@pytest.mark.asyncio
async def test_parse_traffic_info_missing_header(traffic_updater):  # noqa: PT019, PT006
    """Тест отсутствия заголовка Subscription-Userinfo."""
    response_data = {"headers": {}}

    result = await traffic_updater.parse_traffic_info(response_data)

    assert result is None


@pytest.mark.asyncio
async def test_update_key_with_traffic_success(
    traffic_updater, mock_pool, sample_key, sample_client
):  # noqa: PT019, PT006
    """Тест успешного обновления ключа трафиком."""
    traffic_data = {
        "headers": {"Subscription-Userinfo": "upload=1000; download=2000; total=10000"}
    }

    result = await traffic_updater.update_key_with_traffic(
        mock_pool, sample_key, sample_client, traffic_data
    )

    assert result is True
    assert sample_key.used_traffic == 3000
    assert sample_key.total_gb == 10000
    assert sample_key.expiry_time == sample_client.expiry_time
    assert sample_key.limit_ip == sample_client.limit_ip
    traffic_updater.model_data.keys.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_key_with_traffic_no_data(
    traffic_updater, mock_pool, sample_key, sample_client
):  # noqa: PT019, PT006
    """Тест обновления ключа без данных о трафике."""
    result = await traffic_updater.update_key_with_traffic(
        mock_pool, sample_key, sample_client, None
    )

    assert result is False
