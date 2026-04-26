"""
Tests for PriceService — единый сервис расчёта цены со скидкой.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.stocks.stock import Stock
from models.tariffs.tariff import Tariff
from services.core.price.form_price import Pricing
from services.core.price.result import PriceResult
from services.core.price.service import PriceService


def make_tariff(tariff_id: int = 1, amount: Decimal = Decimal("100.00")) -> Tariff:
    tariff = MagicMock(spec=Tariff)
    tariff.id = tariff_id
    tariff.amount = amount
    tariff.name_tariff = f"Tariff-{tariff_id}"
    return tariff


def make_stock(
    stock_type: str = "fix",
    value: Decimal = Decimal("20.00"),
    is_active: bool = True,
    valid_until=None,
) -> Stock:
    return Stock(
        tg_id=123,
        stock_type=stock_type,
        value=value,
        is_active=is_active,
        valid_until=valid_until,
    )


def make_service(stock=None):
    pricing = Pricing()
    model_data = MagicMock()
    model_data.stocks.get_data = AsyncMock(return_value=stock)
    return PriceService(pricing=pricing, model_data=model_data)


class TestCalculateWithoutDiscount:
    """calculate() без скидки — original = final."""

    @pytest.mark.asyncio
    async def test_no_stock(self):
        service = make_service(stock=None)
        tariff = make_tariff(amount=Decimal("100.00"))

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.original_amount == Decimal("100.00")
        assert result.final_amount == Decimal("100.00")
        assert result.has_discount is False
        assert result.stock_value == 0
        assert result.stock_type == ""

    @pytest.mark.asyncio
    async def test_inactive_stock(self):
        stock = make_stock(is_active=False)
        service = make_service(stock=stock)
        tariff = make_tariff(amount=Decimal("100.00"))

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is False
        assert result.final_amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_expired_stock(self):
        past = datetime.utcnow() - timedelta(days=1)
        stock = make_stock(valid_until=past)
        service = make_service(stock=stock)
        tariff = make_tariff(amount=Decimal("100.00"))

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is False
        assert result.final_amount == Decimal("100.00")


class TestCalculateWithFixDiscount:
    """calculate() с фиксированной скидкой."""

    @pytest.mark.asyncio
    async def test_fix_discount(self):
        stock = make_stock(stock_type="fix", value=Decimal("20.00"))
        service = make_service(stock=stock)
        tariff = make_tariff(amount=Decimal("100.00"))

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is True
        assert result.original_amount == Decimal("100.00")
        assert result.final_amount == Decimal("80.00")
        assert result.stock_value == Decimal("20.00")
        assert result.stock_type == "fix"


class TestCalculateWithPercentDiscount:
    """calculate() с процентной скидкой."""

    @pytest.mark.asyncio
    async def test_percent_discount(self):
        stock = make_stock(stock_type="percent", value=Decimal("25"))
        service = make_service(stock=stock)
        tariff = make_tariff(amount=Decimal("200.00"))

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is True
        assert result.original_amount == Decimal("200.00")
        assert result.final_amount == Decimal("150.00")
        assert result.stock_type == "percent"


class TestCalculateBatch:
    """calculate_batch() — один запрос Stock на N тарифов."""

    @pytest.mark.asyncio
    async def test_batch_single_stock_call(self):
        stock = make_stock(stock_type="fix", value=Decimal("10.00"))
        service = make_service(stock=stock)

        tariffs = [
            make_tariff(tariff_id=1, amount=Decimal("100.00")),
            make_tariff(tariff_id=2, amount=Decimal("200.00")),
            make_tariff(tariff_id=3, amount=Decimal("50.00")),
        ]

        results = await service.calculate_batch(tg_id=123, tariffs=tariffs)

        assert len(results) == 3
        assert results[1].final_amount == Decimal("90.00")
        assert results[2].final_amount == Decimal("190.00")
        assert results[3].final_amount == Decimal("40.00")

        # Stock загружен ровно один раз
        service._stock_data.get_data.assert_awaited_once_with(123)


class TestTotal:
    """total(months) — правильное умножение."""

    def test_total_single_month(self):
        result = PriceResult(
            original_amount=Decimal("100.00"),
            final_amount=Decimal("80.00"),
            stock_value=Decimal("20.00"),
            stock_type="fix",
            has_discount=True,
        )
        assert result.total(1) == 80.0

    def test_total_multiple_months(self):
        result = PriceResult(
            original_amount=Decimal("100.00"),
            final_amount=Decimal("80.00"),
            stock_value=Decimal("20.00"),
            stock_type="fix",
            has_discount=True,
        )
        assert result.total(3) == 240.0

    def test_total_default_one_month(self):
        result = PriceResult(
            original_amount=Decimal("50.00"),
            final_amount=Decimal("50.00"),
            stock_value=0,
            stock_type="",
            has_discount=False,
        )
        assert result.total() == 50.0


class TestCalculateSync:
    """calculate_sync() — когда Stock уже загружен."""

    def test_sync_with_stock(self):
        stock = make_stock(stock_type="percent", value=Decimal("10"))
        service = make_service()
        tariff = make_tariff(amount=Decimal("100.00"))

        result = service.calculate_sync(tariff=tariff, stock=stock)

        assert result.has_discount is True
        assert result.final_amount == Decimal("90.00")

    def test_sync_without_stock(self):
        service = make_service()
        tariff = make_tariff(amount=Decimal("100.00"))

        result = service.calculate_sync(tariff=tariff, stock=None)

        assert result.has_discount is False
        assert result.final_amount == Decimal("100.00")
