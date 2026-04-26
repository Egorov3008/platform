import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.core.payment.renewal_service import KeyRenewalService
from services.core.payment.processor import PaymentProcessor


def test_key_renewal_service_initialization():
    """Тест инициализации KeyRenewalService."""
    processor = AsyncMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    service = KeyRenewalService(processor, key_manager)

    assert service.processor == processor
    assert service.key_manager == key_manager
    assert service.builder is not None


@pytest.mark.asyncio
@patch("services.core.payment.renewal_service.bot", new_callable=AsyncMock)
async def test_process_success(mock_bot):
    """Тест успешного процесса продления ключа без кеша (fallback на key.tariff_id)."""
    processor = MagicMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    processor.extract_operation.return_value = ("renew_key", "test@example.com")
    processor.tg_id = 123456789
    processor.number_of_months = 3
    processor.amount = 99.99
    processor._conn = AsyncMock()

    # Моки для загрузки данных
    mock_key = MagicMock()
    mock_key.tariff_id = 1
    mock_key.tg_id = 123456789
    mock_key.email = "test@example.com"
    mock_key.key = "test_key"
    mock_key.name_tariff = "Premium"
    mock_key.expiry_time = int(datetime(2024, 12, 31, 23, 59).timestamp() * 1000)
    mock_key.total_gb = 100 * (2**30)

    mock_tariff = MagicMock()
    mock_tariff.id = 1

    mock_user = MagicMock()
    mock_user.server_id = 1

    mock_server = MagicMock()

    processor._model_service = AsyncMock()
    processor._model_service.keys.get_data = AsyncMock(return_value=mock_key)
    processor._model_service.tariffs.get_data = AsyncMock(return_value=mock_tariff)
    processor._model_service.users.get_data = AsyncMock(return_value=mock_user)
    processor._model_service.servers.get_data = AsyncMock(return_value=mock_server)

    # Кеш пустой - возвращает None
    processor._cache = AsyncMock()
    processor._cache.tariffs.temporary_get = AsyncMock(return_value=None)

    # extension_key возвращает обновлённый ключ
    key_manager.extension_key.return_value = mock_key

    service = KeyRenewalService(processor, key_manager)
    await service.process(email="test@example.com")

    # extract_operation не вызывается, т.к. email передан
    processor.extract_operation.assert_not_called()
    
    # Проверяем, что тариф загружен по key.tariff_id (fallback)
    processor._model_service.tariffs.get_data.assert_called_with(1)
    
    key_manager.extension_key.assert_called_once_with(
        key=mock_key,
        conn=processor._conn,
        server=mock_server,
        tariff=mock_tariff,
        number_of_months=3,
    )

    mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
@patch("services.core.payment.renewal_service.bot", new_callable=AsyncMock)
async def test_process_uses_cached_tariff_id(mock_bot):
    """Тест использования tariff_id из кеша при продлении пробного ключа."""
    processor = MagicMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    processor.extract_operation.return_value = ("renew_key", "trial@example.com")
    processor.tg_id = 123456789
    processor.number_of_months = 1
    processor.amount = 100.0
    processor._conn = AsyncMock()

    # Пробный ключ с tariff_id=10
    mock_key = MagicMock()
    mock_key.tariff_id = 10  # Пробный тариф
    mock_key.tg_id = 123456789
    mock_key.email = "trial@example.com"
    mock_key.key = "trial_key"
    mock_key.name_tariff = "Trial"
    mock_key.expiry_time = int(datetime(2024, 12, 31, 23, 59).timestamp() * 1000)
    mock_key.total_gb = 50 * (2**30)

    # Выбранный тариф (платный)
    mock_selected_tariff = MagicMock()
    mock_selected_tariff.id = 2  # Выбран тариф id=2

    mock_user = MagicMock()
    mock_user.server_id = 1

    mock_server = MagicMock()

    processor._model_service = AsyncMock()
    processor._model_service.keys.get_data = AsyncMock(return_value=mock_key)
    processor._model_service.tariffs.get_data = AsyncMock(return_value=mock_selected_tariff)
    processor._model_service.users.get_data = AsyncMock(return_value=mock_user)
    processor._model_service.servers.get_data = AsyncMock(return_value=mock_server)

    # Кеш возвращает выбранный tariff_id=2
    processor._cache = AsyncMock()
    processor._cache.tariffs.temporary_get = AsyncMock(
        return_value={"tariff_id": 2}
    )

    key_manager.extension_key.return_value = mock_key

    service = KeyRenewalService(processor, key_manager)
    await service.process(email="trial@example.com")

    # Проверяем, что тариф загружен по tariff_id из кеша (2), а не из ключа (10)
    processor._model_service.tariffs.get_data.assert_called_with(2)
    
    # Проверяем, что кеш был очищен
    processor._cache.tariffs.delete.assert_called_once_with("renewal_tariff_trial@example.com")
    
    key_manager.extension_key.assert_called_once_with(
        key=mock_key,
        conn=processor._conn,
        server=mock_server,
        tariff=mock_selected_tariff,
        number_of_months=1,
    )


@pytest.mark.asyncio
@patch("services.core.payment.renewal_service.bot", new_callable=AsyncMock)
async def test_process_cache_miss_fallback_to_key_tariff(mock_bot):
    """Тест fallback на key.tariff_id при отсутствии кеша."""
    processor = MagicMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    processor.extract_operation.return_value = ("renew_key", "user@example.com")
    processor.tg_id = 123456789
    processor.number_of_months = 2
    processor.amount = 200.0
    processor._conn = AsyncMock()

    mock_key = MagicMock()
    mock_key.tariff_id = 3  # Платный тариф
    mock_key.tg_id = 123456789
    mock_key.email = "user@example.com"
    mock_key.key = "user_key"
    mock_key.name_tariff = "Standard"
    mock_key.expiry_time = int(datetime(2024, 12, 31, 23, 59).timestamp() * 1000)
    mock_key.total_gb = 100 * (2**30)

    mock_tariff = MagicMock()
    mock_tariff.id = 3

    mock_user = MagicMock()
    mock_user.server_id = 1

    mock_server = MagicMock()

    processor._model_service = AsyncMock()
    processor._model_service.keys.get_data = AsyncMock(return_value=mock_key)
    processor._model_service.tariffs.get_data = AsyncMock(return_value=mock_tariff)
    processor._model_service.users.get_data = AsyncMock(return_value=mock_user)
    processor._model_service.servers.get_data = AsyncMock(return_value=mock_server)

    # Кеш возвращает None (нет выбранного тарифа)
    processor._cache = AsyncMock()
    processor._cache.tariffs.temporary_get = AsyncMock(return_value=None)

    key_manager.extension_key.return_value = mock_key

    service = KeyRenewalService(processor, key_manager)
    await service.process(email="user@example.com")

    # Проверяем, что тариф загружен по key.tariff_id (fallback)
    processor._model_service.tariffs.get_data.assert_called_with(3)
    
    # Кеш не должен был очищаться (не было selected_tariff_id)
    processor._cache.tariffs.delete.assert_not_called()


@pytest.mark.asyncio
@patch("services.core.payment.renewal_service.bot", new_callable=AsyncMock)
async def test_process_cache_delete_error_handled(mock_bot):
    """Тест обработки ошибки при очистке кеша."""
    processor = MagicMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    processor.extract_operation.return_value = ("renew_key", "user@example.com")
    processor.tg_id = 123456789
    processor.number_of_months = 1
    processor.amount = 100.0
    processor._conn = AsyncMock()

    mock_key = MagicMock()
    mock_key.tariff_id = 10
    mock_key.tg_id = 123456789
    mock_key.email = "user@example.com"
    mock_key.key = "key"
    mock_key.name_tariff = "Trial"
    mock_key.expiry_time = int(datetime(2024, 12, 31, 23, 59).timestamp() * 1000)
    mock_key.total_gb = 50 * (2**30)

    mock_tariff = MagicMock()
    mock_tariff.id = 1

    mock_user = MagicMock()
    mock_user.server_id = 1

    mock_server = MagicMock()

    processor._model_service = AsyncMock()
    processor._model_service.keys.get_data = AsyncMock(return_value=mock_key)
    processor._model_service.tariffs.get_data = AsyncMock(return_value=mock_tariff)
    processor._model_service.users.get_data = AsyncMock(return_value=mock_user)
    processor._model_service.servers.get_data = AsyncMock(return_value=mock_server)

    # Кеш возвращает выбранный тариф
    processor._cache = AsyncMock()
    processor._cache.tariffs.temporary_get = AsyncMock(return_value={"tariff_id": 1})
    # Ошибка при очистке кеша
    processor._cache.tariffs.delete = AsyncMock(side_effect=Exception("Redis error"))

    key_manager.extension_key.return_value = mock_key

    service = KeyRenewalService(processor, key_manager)
    # Ошибка очистки кеша не должна прерывать процесс
    await service.process(email="user@example.com")

    # Продление должно завершиться успешно
    key_manager.extension_key.assert_called_once()
    # Кеш должен был быть очищен (попытка)
    processor._cache.tariffs.delete.assert_called_once()
    # Сообщение отправлено
    mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_process_wrong_operation():
    """Тест обработки неправильной операции."""
    processor = MagicMock(spec=PaymentProcessor)
    processor.tg_id = 123

    key_manager = AsyncMock()

    processor.extract_operation.return_value = ("wrong_operation", "test@example.com")

    service = KeyRenewalService(processor, key_manager)

    with pytest.raises(
        ValueError, match="Ожидалась операция 'renew_key', получено: wrong_operation"
    ):
        await service.process()

    processor.extract_operation.assert_called_once()
    key_manager.extension_key.assert_not_called()


@pytest.mark.asyncio
async def test_process_exception_handling():
    """Тест обработки исключения в процессе продления ключа."""
    processor = MagicMock(spec=PaymentProcessor)
    processor.tg_id = 123
    processor.number_of_months = 1
    processor.amount = 99.99
    processor._conn = AsyncMock()
    key_manager = AsyncMock()

    mock_key = MagicMock()
    mock_key.tariff_id = 1
    mock_user = MagicMock()
    mock_user.server_id = 1
    mock_tariff = MagicMock()
    mock_tariff.id = 1
    mock_tariff.amount = 100.0

    processor._model_service = AsyncMock()
    processor._model_service.keys.get_data = AsyncMock(return_value=mock_key)
    processor._model_service.tariffs.get_data = AsyncMock(return_value=mock_tariff)
    processor._model_service.users.get_data = AsyncMock(return_value=mock_user)
    processor._model_service.servers.get_data = AsyncMock(return_value=MagicMock())

    # Кеш пустой
    processor._cache = AsyncMock()
    processor._cache.tariffs.temporary_get = AsyncMock(return_value=None)

    key_manager.extension_key.side_effect = Exception("API error")

    service = KeyRenewalService(processor, key_manager)

    with pytest.raises(Exception, match="API error"):
        await service.process(email="test@example.com")

    key_manager.extension_key.assert_called_once()


@pytest.mark.asyncio
@patch("services.core.payment.renewal_service.bot", new_callable=AsyncMock)
async def test_send_renewal_message(mock_bot):
    """Тест отправки сообщения о продлении."""
    processor = AsyncMock(spec=PaymentProcessor)
    key_manager = AsyncMock()

    service = KeyRenewalService(processor, key_manager)

    key_details = MagicMock()
    key_details.tg_id = 123456789
    key_details.key = "test_key_123"
    key_details.email = "test@example.com"
    key_details.name_tariff = "Premium"

    new_expiry = datetime(2024, 12, 31, 23, 59)
    traffic_limit = 100

    await service._send_renewal_message(key_details, new_expiry, traffic_limit)

    mock_bot.send_message.assert_called_once()

    args, kwargs = mock_bot.send_message.call_args
    chat_id, text = args

    assert chat_id == 123456789
    assert "test@example.com" in text
    assert "31.12.2024" in text
    assert "Premium" in text
    assert "Техническая поддержка" in kwargs["reply_markup"].inline_keyboard[0][0].text
