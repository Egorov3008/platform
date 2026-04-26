from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from models import User
from services.core.payment.creation_service import KeyCreationService
from services.core.payment.processor import PaymentProcessor


def test_key_creation_service_initialization():
    """Тест инициализации KeyCreationService."""
    processor = AsyncMock(spec=PaymentProcessor)
    create_key = AsyncMock()

    service = KeyCreationService(processor, create_key)

    assert service.processor == processor
    assert service.create_key == create_key
    assert service.builder is not None


@pytest.mark.asyncio
@patch("services.core.payment.creation_service.bot", new_callable=AsyncMock)
async def test_process_success(mock_bot, mock_conn, mock_model_service, mock_cache):
    """Тест успешного процесса создания ключа."""
    # Создаем моки
    processor = AsyncMock(spec=PaymentProcessor)

    processor._model_service = mock_model_service
    create_key = AsyncMock()

    # Настраиваем моки
    processor.extract_operation.return_value = ("create_key", "1")

    # Создаем мок для tariff (через tariffs, а не payments)
    tariff_mock = AsyncMock()
    processor._model_service.tariffs = AsyncMock()
    processor._model_service.tariffs.get_data.return_value = tariff_mock

    # Создаем мок для user
    user = User(
        tg_id=123, username="test", trial=0, created_at=datetime.now(), server_id=1
    )

    processor._model_service.users.get_data.return_value = user
    processor.tg_id = 123
    processor.number_of_months = 1
    processor.amount = 99.99
    # Создаем мок для key_data
    key_data_mock = {"public_link": "test_link", "days": 30}
    create_key.proces.return_value = key_data_mock

    # Мок бота
    processor._conn = AsyncMock()

    # Создаем сервис и вызываем process
    service = KeyCreationService(processor, create_key)

    await service.process(tariff_id="1")

    # Проверяем вызовы — extract_operation не вызывается, т.к. tariff_id передан
    processor.extract_operation.assert_not_called()
    processor._model_service.tariffs.get_data.assert_called_once_with(1)
    processor._model_service.users.get_data.assert_called_once_with(processor.tg_id)
    create_key.proces.assert_called_once_with(
        tg_id=processor.tg_id,
        tariff=tariff_mock,
        server_id=1,
        conn=processor._conn,
        number_of_months=processor.number_of_months,
    )
    # Проверяем отправку сообщения
    mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_process_exception_handling(mock_conn, mock_model_service, mock_cache):
    """Тест обработки исключения в процессе создания ключа."""
    processor = AsyncMock(spec=PaymentProcessor)
    processor._model_service = mock_model_service
    processor._conn = mock_conn
    processor._cache = mock_cache

    processor.tg_id = 123
    processor.number_of_months = 1
    create_key = AsyncMock()
    # Настраиваем мок
    processor._model_service.tariffs = AsyncMock()
    processor._model_service.tariffs.get_data.side_effect = Exception("Database error")

    service = KeyCreationService(processor, create_key)

    with pytest.raises(Exception, match="Database error"):
        await service.process(tariff_id="1")

    # Проверяем вызовы
    processor.extract_operation.assert_not_called()
    processor._model_service.tariffs.get_data.assert_called_once_with(1)
    processor._model_service.users.get_data.assert_not_called()
    create_key.proces.assert_not_called()


@pytest.mark.asyncio
@patch("services.core.payment.creation_service.bot", new_callable=AsyncMock)
async def test_send_key_message(mock_bot):
    """Тест отправки сообщения с ключом."""
    processor = AsyncMock(spec=PaymentProcessor)
    create_key = AsyncMock()

    # Настраиваем моки
    processor.tg_id = 123456789

    # Создаем сервис
    service = KeyCreationService(processor, create_key)

    # Данные ключа
    key_data = {"public_link": "test_link_123", "days": 30}

    # Вызываем приватный метод
    await service._send_key_message(key_data)

    # Проверяем отправку сообщения
    mock_bot.send_message.assert_called_once()

    call_args = mock_bot.send_message.call_args
    assert call_args[1]["chat_id"] == 123456789
    assert "test_link_123" in call_args[1]["text"]
    assert "30" in call_args[1]["text"]
    assert call_args[1]["reply_markup"] is not None
