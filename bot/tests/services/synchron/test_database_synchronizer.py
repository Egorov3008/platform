from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.asyncio
async def test_sync_data_no_clients(database_synchronizer, mock_xui_session):  # noqa: PT019, PT006
    """Тест синхронизации при отсутствии клиентов."""
    # Мокаем извлечение клиентов
    database_synchronizer.xui_fetcher.extract_clients = AsyncMock(return_value=[])

    result = await database_synchronizer.sync_data(mock_xui_session)

    assert result == {"total": 0, "successful": 0, "failed": 0}


@pytest.mark.asyncio
async def test_sync_data_empty_cache_data(
    database_synchronizer, mock_xui_session, sample_client
):  # noqa: PT019, PT006
    """Тест синхронизации с пустыми данными кэша."""
    # Мокаем извлечение клиентов
    database_synchronizer.xui_fetcher.extract_clients = AsyncMock(
        return_value=[sample_client]
    )

    # Мокаем set_cache_data (вызывается перед сравнением)
    database_synchronizer.cache_comparator.set_cache_data = AsyncMock()

    # Мокаем сравнение (отсутствуют в кэше)
    database_synchronizer.cache_comparator.compare = Mock(
        return_value=(["test@example.com"], [12345])
    )

    # Мокаем восстановление данных
    database_synchronizer._restore_missing_data = AsyncMock(
        return_value={"restored_keys": 1, "restored_users": 1}
    )

    # Мокаем обновление трафика
    database_synchronizer._update_traffic_in_batches = AsyncMock(
        return_value={"total": 1, "successful": 1, "failed": 0}
    )

    result = await database_synchronizer.sync_data(mock_xui_session)

    assert result["total"] == 1
    assert result["successful"] == 1
    assert result["failed"] == 0
    assert result["restored_keys"] == 1
    assert result["restored_users"] == 1
    assert result["panel_clients"] == 1
    assert result["missing_keys"] == 1
    assert result["missing_users"] == 1
    database_synchronizer._restore_missing_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_data_success(
    database_synchronizer, mock_xui_session, sample_client
):  # noqa: PT019, PT006
    """Тест успешной полной синхронизации."""
    # Мокаем извлечение клиентов
    database_synchronizer.xui_fetcher.extract_clients = AsyncMock(
        return_value=[sample_client]
    )

    # Мокаем set_cache_data (вызывается перед сравнением)
    database_synchronizer.cache_comparator.set_cache_data = AsyncMock()

    # Мокаем сравнение (нет различий)
    database_synchronizer.cache_comparator.compare = Mock(return_value=([], []))

    # Мокаем восстановление данных
    database_synchronizer._restore_missing_data = AsyncMock(
        return_value={"restored_keys": 0, "restored_users": 0}
    )

    # Мокаем обновление трафика
    database_synchronizer._update_traffic_in_batches = AsyncMock(
        return_value={"total": 1, "successful": 1, "failed": 0}
    )

    result = await database_synchronizer.sync_data(mock_xui_session)

    assert result["total"] == 1
    assert result["successful"] == 1
    assert result["failed"] == 0
    assert result["panel_clients"] == 1
    database_synchronizer._update_traffic_in_batches.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_data_critical_error(database_synchronizer, mock_xui_session):  # noqa: PT019, PT006
    """Тест обработки критической ошибки."""
    # Мокаем извлечение клиентов с ошибкой
    database_synchronizer.xui_fetcher.extract_clients = AsyncMock(
        side_effect=Exception("Test error")
    )

    result = await database_synchronizer.sync_data(mock_xui_session)

    assert result["total"] == 0
    assert "error" in result


@pytest.mark.asyncio
async def test_restore_missing_data(database_synchronizer, sample_client):  # noqa: PT019, PT006
    """Тест восстановления отсутствующих данных."""
    # Мокаем создание пользователя и ключа
    database_synchronizer.key_creator.ensure_user_exists = AsyncMock(return_value=True)
    database_synchronizer.key_creator.create_key = AsyncMock(return_value=None)

    result = await database_synchronizer._restore_missing_data(
        [sample_client], ["test@example.com"], [12345]
    )

    database_synchronizer.key_creator.ensure_user_exists.assert_awaited_once_with(12345)
    database_synchronizer.key_creator.create_key.assert_awaited_once_with(sample_client)
    assert result == {"restored_keys": 0, "restored_users": 1}


@pytest.mark.asyncio
async def test_update_traffic_in_batches_no_server(
    database_synchronizer, sample_client
):  # noqa: PT019, PT006
    """Тест обновления трафика при отсутствии сервера."""
    # Мокаем получение сервера — используется model_data.servers.get_data(2)
    database_synchronizer.model_data.servers.get_data = AsyncMock(return_value=None)

    # Мокаем получение сессии
    database_synchronizer.get_client_session = AsyncMock()

    result = await database_synchronizer._update_traffic_in_batches([sample_client], 50)

    assert result == {"total": 0, "successful": 0, "failed": 1}


@pytest.mark.asyncio
async def test_update_traffic_in_batches_success(
    database_synchronizer, sample_client, mock_http_session
):  # noqa: PT019, PT006
    """Тест успешного обновления трафика пакетно."""
    # Мокаем получение сервера — используется model_data.servers.get_data(2)
    server = AsyncMock()
    server.subscription_url = "https://test-server.com"
    database_synchronizer.model_data.servers.get_data = AsyncMock(return_value=server)

    # Мокаем получение сессии
    database_synchronizer.get_client_session = AsyncMock(return_value=mock_http_session)

    # Мокаем получение трафика
    database_synchronizer.traffic_updater.fetch_traffic_batch = AsyncMock(
        return_value={
            "test@example.com": {
                "headers": {
                    "Subscription-Userinfo": "upload=1000; download=2000; total=10000"
                }
            }
        }
    )

    # Мокаем ключ в кэше — используется model_data.keys.get_data(client.email)
    key = AsyncMock()
    key.email = "test@example.com"
    database_synchronizer.model_data.keys.get_data = AsyncMock(return_value=key)

    # Мокаем обновление ключа
    database_synchronizer.traffic_updater.update_key_with_traffic = AsyncMock(
        return_value=True
    )

    result = await database_synchronizer._update_traffic_in_batches([sample_client], 1)

    assert result == {"total": 1, "successful": 1, "failed": 0}
    database_synchronizer.traffic_updater.update_key_with_traffic.assert_awaited_once()
