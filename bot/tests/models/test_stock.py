import pytest
from decimal import Decimal
from models.stocks.stock import Stock
from datetime import datetime, timedelta


def test_stock_creation():
    # Тест создания скидки
    stock = Stock(tg_id=123456, stock_type="fix", value=10)
    assert stock.tg_id == 123456
    assert stock.stock_type == "fix"
    assert stock.value == 10
    assert stock.is_active == True
    assert stock.created_at is not None

    # Тест создания скидки с процентами
    stock = Stock(tg_id=123456, stock_type="percent", value=10, is_active=False)
    assert stock.tg_id == 123456
    assert stock.stock_type == "percent"
    assert stock.value == 10
    assert stock.is_active == False

    # Тест создания скидки с Decimal
    stock = Stock(tg_id=123456, stock_type="percent", value=Decimal("15.5"))
    assert stock.value == Decimal("15.5")
    assert isinstance(stock.value, Decimal)

    # Тест создания скидки с временем окончания
    valid_until = datetime.utcnow() + timedelta(days=7)
    stock = Stock(tg_id=123456, stock_type="fix", value=10, valid_until=valid_until)
    assert stock.valid_until == valid_until


def test_stock_validation():
    # Тест валидации отрицательного значения
    with pytest.raises(ValueError, match="value не может быть отрицательным"):
        Stock(tg_id=123456, stock_type="fix", value=-10)

    # Тест валидации типа скидки
    with pytest.raises(ValueError, match="stock_type должен быть 'fix' или 'percent'"):
        Stock(tg_id=123456, stock_type="invalid", value=10)

    # Тест валидации типа скидки с None
    with pytest.raises(ValueError, match="stock_type должен быть 'fix' или 'percent'"):
        Stock(tg_id=123456, stock_type=None, value=10)

    # Тест валидации типа скидки с пустой строкой
    with pytest.raises(ValueError, match="stock_type должен быть 'fix' или 'percent'"):
        Stock(tg_id=123456, stock_type="", value=10)


def test_stock_representation():
    # Тест строкового представления
    stock = Stock(tg_id=123456, stock_type="fix", value=10, is_active=True)
    assert (
        repr(stock)
        == "Stock(tg_id=123456, type=fix, value=10, active=True, valid_until=None)"
    )

    valid_until = datetime.utcnow() + timedelta(days=7)
    stock = Stock(
        tg_id=123456,
        stock_type="percent",
        value=25,
        is_active=False,
        valid_until=valid_until,
    )
    assert (
        repr(stock)
        == f"Stock(tg_id=123456, type=percent, value=25, active=False, valid_until={valid_until})"
    )


def test_stock_validity():
    # Тест актуальности скидки
    # Активная скидка без срока действия - всегда действительна
    stock = Stock(tg_id=123456, stock_type="fix", value=10)
    assert stock.is_valid == True

    # Неактивная скидка - не действительна
    stock = Stock(tg_id=123456, stock_type="fix", value=10, is_active=False)
    assert stock.is_valid == False

    # Скидка с истекшим сроком действия - не действительна
    valid_until = datetime.utcnow() - timedelta(days=1)
    stock = Stock(tg_id=123456, stock_type="fix", value=10, valid_until=valid_until)
    assert stock.is_valid == False

    # Скидка с будущим сроком действия - действительна
    valid_until = datetime.utcnow() + timedelta(days=1)
    stock = Stock(tg_id=123456, stock_type="fix", value=10, valid_until=valid_until)
    assert stock.is_valid == True

    # Скидка с точной датой окончания - действительна до включительно
    valid_until = datetime.utcnow() + timedelta(seconds=1)
    stock = Stock(tg_id=123456, stock_type="fix", value=10, valid_until=valid_until)
    assert stock.is_valid == True

    # Проверка граничного случая - скидка с истекшим сроком на 1 секунду
    valid_until = datetime.utcnow() - timedelta(seconds=1)
    stock = Stock(tg_id=123456, stock_type="fix", value=10, valid_until=valid_until)
    assert stock.is_valid == False
