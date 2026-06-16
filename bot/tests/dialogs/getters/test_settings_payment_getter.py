"""
Tests for SettingsPaymentGetter - payment configuration with discounts.

SettingsPaymentGetter.get_data() prepares payment params with discounted amounts.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Tariff, User
from models.stocks.stock import Stock
from dialogs.windows.getters.payment.setting_payment import SettingsPayment, PaymentContext
from services.core.price.result import PriceResult, apply_volume_discount


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data"""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    manager.start_data = {}
    return manager


@pytest.fixture
def mock_price_service():
    """Mock PriceService"""
    return AsyncMock()


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient: no balance, no referral discount."""
    backend = AsyncMock()
    backend.get_user = AsyncMock(
        return_value={"tg_id": 123456789, "balance": 0.0}
    )
    return backend


@pytest.fixture
def sample_tariff():
    """Sample Tariff"""
    return Tariff(
        id=1,
        name_tariff="Premium",
        amount=49.99,
        period=30,
        traffic_limit=100,
        limit_ip=5,
    )


class TestPaymentContext:
    """Test PaymentContext dataclass"""

    def test_payment_context_creation(self, sample_tariff):
        """PaymentContext should be created with valid data"""
        context = PaymentContext(
            payment_type="create_key|1",
            tariff=sample_tariff,
            number_of_months=1,
            amount=49.99,
            discounted_amount=None,
        )
        assert context.payment_type == "create_key|1"
        assert context.tariff == sample_tariff
        assert context.number_of_months == 1

    def test_payment_context_has_precomputed_discount_when_set(self, sample_tariff):
        """has_precomputed_discount should be True when discounted_amount is set"""
        context = PaymentContext(
            payment_type="create_key|1",
            tariff=sample_tariff,
            number_of_months=1,
            amount=49.99,
            discounted_amount=39.99,
        )
        assert context.has_precomputed_discount is True

    def test_payment_context_has_precomputed_discount_when_none(self, sample_tariff):
        """has_precomputed_discount should be False when discounted_amount is None"""
        context = PaymentContext(
            payment_type="create_key|1",
            tariff=sample_tariff,
            number_of_months=1,
            amount=49.99,
            discounted_amount=None,
        )
        assert context.has_precomputed_discount is False

    def test_payment_context_base_price_with_discount(self, sample_tariff):
        """base_price should return discounted_amount when available"""
        context = PaymentContext(
            payment_type="create_key|1",
            tariff=sample_tariff,
            number_of_months=1,
            amount=49.99,
            discounted_amount=39.99,
        )
        assert context.base_price == 39.99

    def test_payment_context_base_price_without_discount(self, sample_tariff):
        """base_price should return amount when no discount"""
        context = PaymentContext(
            payment_type="create_key|1",
            tariff=sample_tariff,
            number_of_months=1,
            amount=49.99,
            discounted_amount=None,
        )
        assert context.base_price == 49.99

    def test_payment_context_raises_on_missing_payment_type(self, sample_tariff):
        """PaymentContext should raise ValueError when payment_type is None"""
        with pytest.raises(ValueError, match="Отсутствует payment_type"):
            PaymentContext(
                payment_type=None,
                tariff=sample_tariff,
                number_of_months=1,
                amount=49.99,
                discounted_amount=None,
            )

    def test_payment_context_raises_on_missing_tariff(self):
        """PaymentContext should raise ValueError when tariff is None"""
        with pytest.raises(ValueError, match="Отсутствует tariff"):
            PaymentContext(
                payment_type="create_key|1",
                tariff=None,
                number_of_months=1,
                amount=49.99,
                discounted_amount=None,
            )


class TestSettingsPaymentGetterBasic:
    """Test SettingsPaymentGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_with_dialog_data(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should return payment params from dialog_data"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result is not None
        assert result["tariff_name"] == "Premium"
        assert result["number_of_months"] == 1

    @pytest.mark.asyncio
    async def test_get_data_with_discounted_amount(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should use discounted_amount if available"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "discounted_amount": 39.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should use discounted_amount
        assert result["amount"] == 39.99

    @pytest.mark.asyncio
    async def test_get_data_without_discounted_amount(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should use original amount when no discount"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }
        # PriceService вернёт без скидки
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=49.99,
            final_amount=49.99,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should use original amount (no stock discount found either)
        assert result["amount"] == 49.99

    @pytest.mark.asyncio
    async def test_get_data_multiple_months(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should handle multiple months"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "renewal|3",
            "number_of_months": 3,
            "amount": 149.97,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["number_of_months"] == 3

    @pytest.mark.asyncio
    async def test_get_data_with_start_data(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should use start_data when dialog_data empty"""
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.start_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Premium"


class TestSettingsPaymentGetterDiscounts:
    """Test SettingsPaymentGetter discount handling"""

    @pytest.mark.asyncio
    async def test_get_data_discount_priority(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should prioritize discounted_amount over amount"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "discounted_amount": 29.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # discounted_amount should take precedence
        assert result["amount"] == 29.99

    @pytest.mark.asyncio
    async def test_get_data_zero_discount_uses_amount(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should use amount when discounted_amount is None"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "discounted_amount": None,
        }
        # PriceService для прямого входа
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=49.99,
            final_amount=49.99,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Should fall back to amount
        assert result["amount"] == 49.99

    @pytest.mark.asyncio
    async def test_get_data_stock_discount_on_direct_entry(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() должен вычислять скидку Stock при прямом входе в setting_pay"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "renew_key|test@example.com",
            "number_of_months": 1,
            "amount": 49.99,
            # discounted_amount отсутствует — прямой вход
        }

        mock_price_service.calculate.return_value = PriceResult(
            original_amount=49.99,
            final_amount=39.99,
            stock_value=20,
            stock_type="percent",
            has_discount=True,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Скидка Stock должна быть применена
        assert result["amount"] == 39.99
        mock_price_service.calculate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_no_stock_recalc_when_discounted(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() не должен пересчитывать скидку, если discounted_amount уже есть"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "discounted_amount": 39.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # PriceService.calculate не должен вызываться — скидка уже вычислена
        mock_price_service.calculate.assert_not_called()
        assert result["amount"] == 39.99


class TestSettingsPaymentGetterDialogData:
    """Test SettingsPaymentGetter dialog_data persistence"""

    @pytest.mark.asyncio
    async def test_get_data_updates_dialog_data(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should update dialog_data with payment params"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|1"
        assert mock_dialog_manager.dialog_data["number_of_months"] == 1
        assert mock_dialog_manager.dialog_data["tariff"] == sample_tariff

    @pytest.mark.asyncio
    async def test_get_data_sets_discounted_amount_in_dialog(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should set discounted_amount in dialog_data"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "discounted_amount" in mock_dialog_manager.dialog_data


class TestSettingsPaymentGetterErrorHandling:
    """Test SettingsPaymentGetter error handling"""

    @pytest.mark.asyncio
    async def test_get_data_missing_payment_type(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should call dialog_manager.start() and event.answer() when payment_type missing"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "number_of_months": 1,
            "amount": 49.99,
        }
        mock_dialog_manager.start.return_value = AsyncMock()
        mock_dialog_manager.event.answer = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.start.called
        assert mock_dialog_manager.event.answer.called

    @pytest.mark.asyncio
    async def test_get_data_missing_tariff(
        self, mock_price_service, mock_backend, mock_dialog_manager
    ):
        """get_data() should handle missing tariff"""
        mock_dialog_manager.dialog_data = {
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "tariff": None,
        }
        mock_dialog_manager.start.return_value = AsyncMock()
        mock_dialog_manager.event.answer = AsyncMock()

        getter = SettingsPayment(mock_price_service, mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.event.answer.called


class TestSettingsPaymentGetterIntegration:
    """Integration tests for SettingsPaymentGetter"""

    @pytest.mark.asyncio
    async def test_get_data_full_payment_flow(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should handle complete payment setup flow with volume discount"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 2,
            "amount": 99.98,
            "discounted_amount": 96.98,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Premium"
        assert result["number_of_months"] == 2
        # discounted_amount=96.98 per-month, 2 months = 193.96, volume 3% off = 188.1412 → 188.14
        assert result["amount"] == 188.14
        assert result["has_volume_discount"] is True
        assert result["volume_discount_percent"] == 3
        assert result["amount_without_volume_discount"] == 193.96

        assert mock_dialog_manager.dialog_data["payment_type"] == "create_key|1"

    @pytest.mark.asyncio
    async def test_get_data_renewal_flow(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() should handle renewal payment type"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "renewal|3",
            "number_of_months": 3,
            "amount": 149.97,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Premium"
        assert result["number_of_months"] == 3
        assert "renewal" in mock_dialog_manager.dialog_data["payment_type"]

    @pytest.mark.asyncio
    async def test_get_data_tariff_from_amount(
        self, mock_price_service, mock_backend, mock_dialog_manager
    ):
        """get_data() should use tariff.amount when amount not in data"""
        sample_tariff = Tariff(
            id=2,
            name_tariff="Basic",
            amount=19.99,
            period=30,
            traffic_limit=50,
            limit_ip=1,
        )
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|2",
            "number_of_months": 1,
            "amount": 19.99,
        }
        # Прямой вход без скидки
        mock_price_service.calculate.return_value = PriceResult(
            original_amount=19.99,
            final_amount=19.99,
            stock_value=0,
            stock_type="",
            has_discount=False,
        )

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["amount"] == 19.99


class TestVolumeDiscount:
    """Тесты скидки за объём"""

    def test_apply_volume_discount_1_month(self):
        """Без скидки за 1 месяц"""
        total, before, percent = apply_volume_discount(100.0, 1)
        assert total == 100.0
        assert before == 100.0
        assert percent == 0

    def test_apply_volume_discount_2_months(self):
        """3% скидка за 2 месяца"""
        total, before, percent = apply_volume_discount(100.0, 2)
        assert total == 194.0
        assert before == 200.0
        assert percent == 3

    def test_apply_volume_discount_3_months(self):
        """3% скидка за 3 месяца"""
        total, before, percent = apply_volume_discount(100.0, 3)
        assert total == 291.0
        assert before == 300.0
        assert percent == 3

    def test_apply_volume_discount_with_fractional_price(self):
        """Скидка с дробной ценой"""
        total, before, percent = apply_volume_discount(49.99, 2)
        assert total == 96.98  # 49.99 * 2 * 0.97 = 96.9806 → 96.98
        assert before == 99.98
        assert percent == 3

    @pytest.mark.asyncio
    async def test_volume_discount_for_2_months_in_getter(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() должен применять 3% скидку за 2 месяца"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 2,
            "amount": 49.99,
            "discounted_amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # 49.99 * 2 = 99.98, скидка 3% = 96.9806 → 96.98
        assert result["amount"] == 96.98
        assert result["has_volume_discount"] is True
        assert result["volume_discount_percent"] == 3
        assert result["amount_without_volume_discount"] == 99.98

    @pytest.mark.asyncio
    async def test_volume_discount_for_3_months_in_getter(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() должен применять 3% скидку за 3 месяца"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 3,
            "amount": 49.99,
            "discounted_amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # 49.99 * 3 = 149.97, скидка 3% = 145.4709 → 145.47
        assert result["amount"] == 145.47
        assert result["has_volume_discount"] is True
        assert result["volume_discount_percent"] == 3

    @pytest.mark.asyncio
    async def test_no_volume_discount_for_1_month_in_getter(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """get_data() не должен применять скидку за 1 месяц"""
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
            "discounted_amount": 49.99,
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["amount"] == 49.99
        assert result["has_volume_discount"] is False
        assert result["volume_discount_percent"] == 0

    @pytest.mark.asyncio
    async def test_volume_and_stock_discounts_stack(
        self, mock_price_service, mock_backend, mock_dialog_manager, sample_tariff
    ):
        """Stock + Volume скидки стакаются мультипликативно"""
        # Stock-скидка уже применена: 49.99 → 39.99 за месяц
        mock_dialog_manager.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 3,
            "amount": 49.99,
            "discounted_amount": 39.99,  # после Stock-скидки
        }

        getter = SettingsPayment(mock_price_service, mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # 39.99 * 3 = 119.97, volume 3% off = 116.3709 → 116.37
        assert result["amount"] == 116.37
        assert result["has_volume_discount"] is True
        assert result["amount_without_volume_discount"] == 119.97


class TestSettingsPaymentConcurrency:
    """Test SettingsPayment for race conditions and concurrent access"""

    @pytest.mark.asyncio
    async def test_no_shared_state_between_concurrent_calls(
        self, mock_price_service, mock_backend, sample_tariff
    ):
        """get_data() should not share state between concurrent calls from different users"""
        # Create two separate dialog managers for different users
        manager_a = AsyncMock()
        manager_a.event = MagicMock()
        manager_a.event.from_user = MagicMock()
        manager_a.event.from_user.id = 111111111
        manager_a.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "create_key|1",
            "number_of_months": 1,
            "amount": 49.99,
        }
        manager_a.start_data = {}

        manager_b = AsyncMock()
        manager_b.event = MagicMock()
        manager_b.event.from_user = MagicMock()
        manager_b.event.from_user.id = 222222222
        manager_b.dialog_data = {
            "tariff": sample_tariff,
            "payment_type": "renewal|3",
            "number_of_months": 2,
            "amount": 99.98,
        }
        manager_b.start_data = {}

        getter = SettingsPayment(mock_price_service, mock_backend)

        # Run both requests concurrently
        result_a, result_b = await asyncio.gather(
            getter.get_data(manager_a),
            getter.get_data(manager_b),
        )

        # Each user should get their own data, not mixed/overwritten
        assert result_a["number_of_months"] == 1
        assert result_b["number_of_months"] == 2

        # Verify dialog_data is independent
        assert manager_a.dialog_data["number_of_months"] == 1
        assert manager_b.dialog_data["number_of_months"] == 2
