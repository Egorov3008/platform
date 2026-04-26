import pytest
from unittest.mock import AsyncMock, MagicMock

from models.payments.payment import PaymentModel
from services.core.payment.processor import PaymentProcessor


def create_mock_dependencies():
    """Создает моки зависимостей для PaymentProcessor."""
    conn = AsyncMock()

    # Мок model_service
    model_service = MagicMock()
    payment_data_mock = AsyncMock()
    model_service.payments = payment_data_mock

    # Мок cache
    cache = MagicMock()
    payments_cache = AsyncMock()
    cache.payments = payments_cache

    return conn, model_service, cache


def test_payment_processor_initialization():
    """Тест инициализации PaymentProcessor."""
    conn, model_service, cache = create_mock_dependencies()

    processor = PaymentProcessor(conn, model_service, cache)

    assert processor._conn == conn
    assert processor._model_service == model_service
    assert processor._cache == cache
    assert processor.amount is None
    assert processor.payment_type is None
    assert processor.tg_id is None
    assert processor.number_of_months is None
    assert processor.status is None


def test_extract_operation_success():
    """Тест успешного извлечения операции из payment_type."""
    conn, model_service, cache = create_mock_dependencies()
    processor = PaymentProcessor(conn, model_service, cache)

    processor.payment_type = "renewal|12345"
    result = processor.extract_operation()

    assert result == ["renewal", "12345"]


def test_extract_operation_failure():
    """Тест извлечения операции при некорректном формате payment_type."""
    conn, model_service, cache = create_mock_dependencies()
    processor = PaymentProcessor(conn, model_service, cache)

    processor.payment_type = "invalid_format"

    with pytest.raises(
        ValueError, match="Некорректный формат payment_type: invalid_format"
    ):
        processor.extract_operation()


def test_extract_operation_empty():
    """Тест извлечения операции при пустом payment_type."""
    conn, model_service, cache = create_mock_dependencies()
    processor = PaymentProcessor(conn, model_service, cache)

    processor.payment_type = ""

    with pytest.raises(ValueError, match="Некорректный формат payment_type: "):
        processor.extract_operation()


def test_extract_operation_multiple_separators():
    """Тест извлечения операции при наличии нескольких разделителей."""
    conn, model_service, cache = create_mock_dependencies()
    processor = PaymentProcessor(conn, model_service, cache)

    processor.payment_type = "renewal|12345|extra"
    result = processor.extract_operation()

    # split("|", 1) делит только по первому вхождению
    assert result == ["renewal", "12345|extra"]


@pytest.mark.asyncio
async def test_load_payment_data_success():
    """Тест успешной загрузки данных платежа из БД."""
    conn, model_service, cache = create_mock_dependencies()

    mock_payment_data = PaymentModel(
        payment_id="test_payment_123",
        amount=99.99,
        payment_type="renewal|12345",
        tg_id=123456789,
        number_of_months=6,
    )

    model_service.payments.get_data.return_value = mock_payment_data

    processor = PaymentProcessor(conn, model_service, cache)
    await processor.load_payment_data("test_payment_123")

    assert processor.amount == 99.99
    assert processor.payment_type == "renewal|12345"
    assert processor.tg_id == 123456789
    assert processor.number_of_months == 6

    model_service.payments.get_data.assert_called_once_with("test_payment_123")


@pytest.mark.asyncio
async def test_load_payment_data_not_found():
    """Тест загрузки данных платежа, который не найден."""
    conn, model_service, cache = create_mock_dependencies()

    model_service.payments.get_data.return_value = None

    processor = PaymentProcessor(conn, model_service, cache)

    with pytest.raises(ValueError, match="Платёж не найден: test_payment_123"):
        await processor.load_payment_data("test_payment_123")

    model_service.payments.get_data.assert_called_once_with("test_payment_123")


@pytest.mark.asyncio
async def test_load_payment_data_default_months():
    """Тест загрузки данных платежа с number_of_months по умолчанию."""
    conn, model_service, cache = create_mock_dependencies()

    mock_payment_data = PaymentModel(
        payment_id="test_payment_123",
        amount=99.99,
        payment_type="renewal|12345",
        tg_id=123456789,
    )

    model_service.payments.get_data.return_value = mock_payment_data

    processor = PaymentProcessor(conn, model_service, cache)
    await processor.load_payment_data("test_payment_123")

    assert processor.number_of_months == 1  # default


@pytest.mark.asyncio
async def test_update_payment_success():
    """Тест успешного обновления платежа (ветка CREATE — платёж не найден)."""
    conn, model_service, cache = create_mock_dependencies()

    model_service.payments.get_data = AsyncMock(return_value=None)

    processor = PaymentProcessor(conn, model_service, cache)
    processor.amount = 99.99
    processor.payment_type = "renewal|12345"
    processor.tg_id = 123456789
    processor.number_of_months = 3

    await processor.update_payment("test_payment_123")

    model_service.payments.save_data.assert_called_once()

    call_args = model_service.payments.save_data.call_args
    assert call_args[0][0] == conn

    saved_payment = call_args[0][1]
    assert isinstance(saved_payment, PaymentModel)
    assert saved_payment.payment_id == "test_payment_123"
    assert saved_payment.amount == 99.99
    assert saved_payment.payment_type == "renewal|12345"
    assert saved_payment.tg_id == 123456789
    assert saved_payment.number_of_months == 3

    assert call_args[1]["payment_id"] == "test_payment_123"


@pytest.mark.asyncio
async def test_update_payment_without_data():
    """Тест обновления платежа без предварительной загрузки данных (ветка CREATE)."""
    conn, model_service, cache = create_mock_dependencies()

    model_service.payments.get_data = AsyncMock(return_value=None)

    processor = PaymentProcessor(conn, model_service, cache)

    await processor.update_payment("test_payment_123")

    model_service.payments.save_data.assert_called_once()

    call_args = model_service.payments.save_data.call_args
    saved_payment = call_args[0][1]

    assert isinstance(saved_payment, PaymentModel)
    assert saved_payment.payment_id == "test_payment_123"
    assert saved_payment.amount is None
    assert saved_payment.payment_type is None
    assert saved_payment.tg_id is None
    assert saved_payment.number_of_months == 1  # default fallback (None or 1)
