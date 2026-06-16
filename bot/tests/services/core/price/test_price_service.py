"""
Tests for PriceService — единый сервис расчёта цены со скидкой.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from models.stocks.stock import Stock
from models.tariffs.tariff import Tariff
from services.core.price.form_price import Pricing
from services.core.price.result import PriceResult
from services.core.price.service import PriceService


def make_tariff(tariff_id: int = 1, amount: float = 100.0) -> Tariff:
    return Tariff(
        id=tariff_id,
        name_tariff=f"Tariff-{tariff_id}",
        amount=amount,
        period=30,
        traffic_limit=0,
    )


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


def make_service(stock_data: dict | None = None):
    """Build PriceService with a backend that returns ``stock_data`` for get_user_stock.

    If ``stock_data`` is None, the backend reports no discount.
    """
    pricing = Pricing()
    backend = AsyncMock()
    backend.get_user_stock = AsyncMock(return_value=stock_data)
    return PriceService(pricing=pricing, backend=backend)


def stock_data_for(stock: Stock | None) -> dict | None:
    """Build a backend-shaped stock dict for the given Stock (or None for no discount)."""
    if stock is None:
        return None
    return {
        "tg_id": stock.tg_id,
        "stock_type": stock.stock_type,
        "value": stock.value,
        "is_active": stock.is_active,
        "valid_until": stock.valid_until,
        "has_discount": True,
    }


class TestCalculateWithoutDiscount:
    """calculate() без скидки — original = final."""

    @pytest.mark.asyncio
    async def test_no_stock(self):
        service = make_service(stock_data=None)
        tariff = make_tariff(amount=100.0)

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.original_amount == 100.0
        assert result.final_amount == 100.0
        assert result.has_discount is False
        assert result.stock_value == 0
        assert result.stock_type == ""

    @pytest.mark.asyncio
    async def test_inactive_stock(self):
        stock = make_stock(is_active=False)
        service = make_service(stock_data=stock_data_for(stock))
        tariff = make_tariff(amount=100.0)

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is False
        assert result.final_amount == 100.0

    @pytest.mark.asyncio
    async def test_expired_stock(self):
        # _fetch_stock сбрасывает valid_until в None («упрощение для бэкенда»),
        # поэтому обходим его и подменяем expired Stock напрямую — это проверяет
        # именно логику is_valid в _apply.
        past = datetime.utcnow() - timedelta(days=1)
        stock = make_stock(valid_until=past)
        service = make_service(stock_data=stock_data_for(stock))
        service._fetch_stock = AsyncMock(return_value=stock)
        tariff = make_tariff(amount=100.0)

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is False
        assert result.final_amount == 100.0


class TestCalculateWithFixDiscount:
    """calculate() с фиксированной скидкой."""

    @pytest.mark.asyncio
    async def test_fix_discount(self):
        stock = make_stock(stock_type="fix", value=Decimal("20.00"))
        service = make_service(stock_data=stock_data_for(stock))
        tariff = make_tariff(amount=100.0)

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is True
        assert result.original_amount == 100.0
        assert result.final_amount == 80.0
        assert result.stock_value == Decimal("20.00")
        assert result.stock_type == "fix"


class TestCalculateWithPercentDiscount:
    """calculate() с процентной скидкой."""

    @pytest.mark.asyncio
    async def test_percent_discount(self):
        stock = make_stock(stock_type="percent", value=Decimal("25"))
        service = make_service(stock_data=stock_data_for(stock))
        tariff = make_tariff(amount=200.0)

        result = await service.calculate(tg_id=123, tariff=tariff)

        assert result.has_discount is True
        assert result.original_amount == 200.0
        assert result.final_amount == 150.0
        assert result.stock_type == "percent"


class TestCalculateBatch:
    """calculate_batch() — один запрос Stock на N тарифов."""

    @pytest.mark.asyncio
    async def test_batch_single_stock_call(self):
        stock = make_stock(stock_type="fix", value=Decimal("10.00"))
        service = make_service(stock_data=stock_data_for(stock))

        tariffs = [
            make_tariff(tariff_id=1, amount=100.0),
            make_tariff(tariff_id=2, amount=200.0),
            make_tariff(tariff_id=3, amount=50.0),
        ]

        results = await service.calculate_batch(tg_id=123, tariffs=tariffs)

        assert len(results) == 3
        assert results[1].final_amount == 90.0
        assert results[2].final_amount == 190.0
        assert results[3].final_amount == 40.0

        # Stock загружен ровно один раз
        service._backend.get_user_stock.assert_awaited_once_with(123)


class TestTotal:
    """total(months) — правильное умножение."""

    def test_total_single_month(self):
        result = PriceResult(
            original_amount=100.0,
            final_amount=80.0,
            stock_value=Decimal("20.00"),
            stock_type="fix",
            has_discount=True,
        )
        assert result.total(1) == 80.0

    def test_total_multiple_months(self):
        result = PriceResult(
            original_amount=100.0,
            final_amount=80.0,
            stock_value=Decimal("20.00"),
            stock_type="fix",
            has_discount=True,
        )
        assert result.total(3) == 240.0

    def test_total_default_one_month(self):
        result = PriceResult(
            original_amount=50.0,
            final_amount=50.0,
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
        tariff = make_tariff(amount=100.0)

        result = service.calculate_sync(tariff=tariff, stock=stock)

        assert result.has_discount is True
        assert result.final_amount == 90.0

    def test_sync_without_stock(self):
        service = make_service()
        tariff = make_tariff(amount=100.0)

        result = service.calculate_sync(tariff=tariff, stock=None)

        assert result.has_discount is False
        assert result.final_amount == 100.0
