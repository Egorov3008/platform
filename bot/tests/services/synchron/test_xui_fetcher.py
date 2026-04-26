from unittest.mock import AsyncMock

import py3xui
import pytest


@pytest.mark.asyncio
async def test_fetch_inbounds_success(xui_fetcher, mock_xui_session):  # noqa: PT019, PT006
    """Тест успешного получения инбаундов."""
    # Настройка мока
    mock_inbound = AsyncMock(return_value=[py3xui.Inbound])
    mock_inbounds = [mock_inbound, mock_inbound]
    mock_xui_session.get_inbounds.return_value = mock_inbounds

    result = await xui_fetcher.fetch_inbounds(mock_xui_session)

    assert result == mock_inbounds
    mock_xui_session.get_inbounds.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_inbounds_error(xui_fetcher, mock_xui_session):  # noqa: PT019, PT006
    """Тест обработки ошибки при получении инбаундов."""
    mock_xui_session.get_inbounds.side_effect = Exception("Connection error")

    result = await xui_fetcher.fetch_inbounds(mock_xui_session)

    assert result == []
    mock_xui_session.get_inbounds.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_clients_success(xui_fetcher, mock_xui_session, sample_client):  # noqa: PT019, PT006
    """Тест успешного извлечения клиентов."""
    # Создаем инбаунд с клиентом
    inbound = AsyncMock(spec=py3xui.Inbound)
    inbound.id = 1
    # Устанавливаем settings.clients как итерируемый объект
    inbound.settings = AsyncMock()
    type(inbound.settings).clients = [sample_client]  # Это важно!

    mock_xui_session.get_inbounds.return_value = [inbound]

    result = await xui_fetcher.extract_clients(mock_xui_session)
    print("Получили результат: ", result)
    assert len(result) == 1
    assert result[0].email == "test@example.com"
    assert result[0].tg_id == 12345


@pytest.mark.asyncio
async def test_extract_clients_no_inbounds(xui_fetcher, mock_xui_session):  # noqa: PT019, PT006
    """Тест извлечения клиентов при отсутствии инбаундов."""
    mock_xui_session.get_inbounds.return_value = []

    result = await xui_fetcher.extract_clients(mock_xui_session)

    assert result == []
