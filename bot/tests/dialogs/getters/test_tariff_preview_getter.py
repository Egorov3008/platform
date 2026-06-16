"""
Tests for TariffPreviewGetter - tariff display data with pricing and discounts.

TariffPreviewGetter.get_data() calls:
- tariff_display.get(tg_id) → list[Tariff]
- price_service.calculate_batch(tg_id, tariffs) → dict[tariff_id, PriceResult]

Result includes: tariff_list (buttons), tariffs (processed), discount_value, discount_type.

Source: dialogs/windows/getters/tariff/preview.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Tariff
from models.stocks.stock import Stock
from dialogs.windows.getters.tariff.preview import TariffPreviewGetter
from services.core.price.result import PriceResult


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with from_user.id."""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    return manager


@pytest.fixture
def mock_tariff_data():
    """Mock TariffData (provides get(user_id) → list[Tariff])."""
    return AsyncMock()


@pytest.fixture
def mock_price_service():
    """Mock PriceService (provides calculate_batch(tg_id, tariffs) → dict)."""
    return AsyncMock()


@pytest.fixture
def sample_tariffs():
    """Sample tariffs."""
    return [
        Tariff(
            id=1,
            name_tariff="Basic",
            amount=19.99,
            period=30,
            traffic_limit=10,
            limit_ip=1,
        ),
        Tariff(
            id=2,
            name_tariff="Premium",
            amount=49.99,
            period=30,
            traffic_limit=50,
            limit_ip=5,
        ),
        Tariff(
            id=3,
            name_tariff="Pro",
            amount=99.99,
            period=30,
            traffic_limit=200,
            limit_ip=10,
        ),
    ]


@pytest.fixture
def sample_stock():
    """Sample valid stock (discount)."""
    return Stock(
        tg_id=123456789,
        stock_type="fix",
        value=10.0,
        is_active=True,
        created_at=datetime.now(),
    )


def _no_discount_results(tariffs):
    """PriceResult без скидки для каждого тарифа."""
    return {
        t.id: PriceResult(
            original_amount=t.amount,
            final_amount=t.amount,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )
        for t in tariffs
    }


def _with_discount_results(tariffs, discount=10.0):
    """PriceResult со скидкой для каждого тарифа."""
    return {
        t.id: PriceResult(
            original_amount=t.amount,
            final_amount=t.amount - discount,
            stock_value=discount,
            stock_type="fix",
            has_discount=True,
        )
        for t in tariffs
    }


# ---------------------------------------------------------------------------
# TariffPreviewGetter — базовая функциональность
# ---------------------------------------------------------------------------


class TestTariffPreviewGetterBasic:
    """Test TariffPreviewGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_with_tariffs_no_discount(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
    ):
        """get_data() should return tariff list without discount."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _no_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        assert "tariff_list" in result
        assert "tariffs" in result
        assert len(result["tariff_list"]) == 3

        # Without discount, discounted_amount should be None
        for value in result["tariffs"].values():
            assert value["discounted_amount"] is None

    @pytest.mark.asyncio
    async def test_get_data_with_tariffs_with_discount(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
        sample_stock,
    ):
        """get_data() should apply discounts to tariff prices."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _with_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        # Should have tariff list
        assert "tariff_list" in result
        # Button text should indicate SALE
        assert any("SALE" in button_text for button_text, _ in result["tariff_list"])

    @pytest.mark.asyncio
    async def test_get_data_no_tariffs(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
    ):
        """get_data() should handle no tariffs available."""
        mock_tariff_data.get.return_value = []
        mock_price_service.calculate_batch.return_value = {}

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_list"] == []
        assert result["tariffs"] == {}

    @pytest.mark.asyncio
    async def test_get_data_calls_services(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
    ):
        """get_data() should call all required services."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _no_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        await getter.get_data(mock_dialog_manager)

        mock_tariff_data.get.assert_called_once_with(123456789)
        mock_price_service.calculate_batch.assert_called_once_with(123456789, sample_tariffs)


# ---------------------------------------------------------------------------
# TariffPreviewGetter — скидки
# ---------------------------------------------------------------------------


class TestTariffPreviewGetterDiscounts:
    """Test TariffPreviewGetter discount handling"""

    @pytest.mark.asyncio
    async def test_get_data_invalid_stock(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
    ):
        """get_data() should ignore inactive stock (PriceService returns no discount)."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _no_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        # Should not have SALE in button text
        assert not any(
            "SALE" in button_text for button_text, _ in result["tariff_list"]
        )

    @pytest.mark.asyncio
    async def test_get_data_processed_tariffs_structure(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
        sample_stock,
    ):
        """get_data() should structure processed_tariffs correctly."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _with_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        # tariffs should have tariff_id as key (string in result)
        processed = result["tariffs"]
        assert "1" in processed

        # Each entry should have tariff and discounted_amount (non-None with discount)
        for _, value in processed.items():
            assert "tariff" in value
            assert "discounted_amount" in value
            assert value["discounted_amount"] is not None

    @pytest.mark.asyncio
    async def test_get_data_saves_processed_tariffs_to_dialog_data(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
    ):
        """get_data() should save processed_tariffs to dialog_data for handlers."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _no_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        await getter.get_data(mock_dialog_manager)

        assert "processed_tariffs" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["processed_tariffs"]) == 3


# ---------------------------------------------------------------------------
# TariffPreviewGetter — интеграция
# ---------------------------------------------------------------------------


class TestTariffPreviewGetterIntegration:
    """Integration tests for TariffPreviewGetter"""

    @pytest.mark.asyncio
    async def test_get_data_full_flow(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
        sample_stock,
    ):
        """get_data() should handle complete tariff preview flow."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = {
            t.id: PriceResult(
                original_amount=t.amount,
                final_amount=39.99,
                stock_value=10.0,
                stock_type="fix",
                has_discount=True,
            )
            for t in sample_tariffs
        }

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        # Should have all required fields
        assert "tariff_list" in result
        assert "tariffs" in result
        assert "discount_value" in result
        assert "discount_type" in result

        # Should process all tariffs
        assert len(result["tariff_list"]) == 3

    @pytest.mark.asyncio
    async def test_get_data_tariff_button_text_without_sale(
        self,
        mock_tariff_data,
        mock_price_service,
        mock_dialog_manager,
        sample_tariffs,
    ):
        """get_data() should use tariff name without sale marker when no discount."""
        mock_tariff_data.get.return_value = sample_tariffs
        mock_price_service.calculate_batch.return_value = _no_discount_results(sample_tariffs)

        getter = TariffPreviewGetter(mock_tariff_data, mock_price_service)
        result = await getter.get_data(mock_dialog_manager)

        # Button text should be tariff names without "SALE"
        button_texts = [text for text, _ in result["tariff_list"]]
        assert "Basic" in button_texts
        assert "Premium" in button_texts
        assert "Pro" in button_texts
