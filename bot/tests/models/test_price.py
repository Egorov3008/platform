import pytest
from models.price_model.price import Price


def test_price_creation():
    # Тест создания цены без скидки
    price = Price(amount=100, stock=0)
    assert price.amount == 100
    assert price.stock == 0
    assert price.type_stock == ""
    assert price.format_price == 100

    # Тест создания цены с фиксированной скидкой
    price = Price(amount=100, stock=10, type_stock="fix")
    assert price.amount == 100
    assert price.stock == 10
    assert price.type_stock == "fix"
    assert price.format_price == 90

    # Тест создания цены с процентной скидкой
    price = Price(amount=100, stock=10, type_stock="percent")
    assert price.amount == 100
    assert price.stock == 10
    assert price.type_stock == "percent"
    assert price.format_price == 90


def test_price_validation():
    # Тест валидации отрицательной суммы
    with pytest.raises(ValueError, match="amount не может быть отрицательным"):
        Price(amount=-100)

    # Тест валидации отрицательной скидки
    with pytest.raises(ValueError, match="stock не может быть отрицательным"):
        Price(amount=100, stock=-10)

    # Тест валидации типа скидки
    with pytest.raises(
        ValueError, match="type_stock должен быть 'fix', 'percent' или пустым"
    ):
        Price(amount=100, stock=10, type_stock="invalid")


def test_price_format_price():
    # Тест итоговой цены с фиксированной скидкой
    price = Price(amount=100, stock=10, type_stock="fix")
    assert price.format_price == 90

    # Тест итоговой цены с процентной скидкой
    price = Price(amount=100, stock=25, type_stock="percent")
    assert price.format_price == 75

    # Тест нулевой скидки
    price = Price(amount=100)
    assert price.format_price == 100

    # Тест скидки больше суммы (должно быть 0)
    price = Price(amount=50, stock=100, type_stock="fix")
    assert price.format_price == 0

    # Тест 100% скидки
    price = Price(amount=100, stock=100, type_stock="percent")
    assert price.format_price == 0


def test_price_representation():
    # Тест строкового представления
    price = Price(amount=100, stock=10, type_stock="fix")
    assert repr(price) == "Price(amount=100, stock=10F)"

    price = Price(amount=100, stock=10, type_stock="percent")
    assert repr(price) == "Price(amount=100, stock=10P)"

    price = Price(amount=100)
    assert repr(price) == "Price(amount=100, stock=0.0)"
