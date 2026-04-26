"""
Tests for PaymentStatsGetter.

PaymentStatsGetter.get_data() fetches:
1. Revenue statistics (year, month, week totals)
2. Revenue forecast (week and month predictions)
3. Formats a user-friendly message with stats and forecasts
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dialogs.windows.getters.admin.payment_stats import PaymentStatsGetter
from services.analytics.payment_metrics import (
    PaymentMetricsService,
    RevenueStats,
    RevenueForecast,
)


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with writable dialog_data."""
    manager = MagicMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_payment_metrics():
    """Mock PaymentMetricsService."""
    metrics = AsyncMock()
    metrics.get_revenue_stats = AsyncMock(
        return_value=RevenueStats(
            year_total=100000.0,
            month_total=15000.0,
            week_total=5000.0,
            day_total=1500.0,
            year_payments_count=50,
            month_payments_count=10,
            week_payments_count=3,
            day_payments_count=1,
            avg_payment_year=2000.0,
            avg_payment_month=1500.0,
            avg_payment_week=1666.67,
            avg_payment_day=1500.0,
        )
    )
    metrics.forecast_revenue = AsyncMock(
        return_value=RevenueForecast(
            week_forecast=5500.0,
            week_confidence=75.0,
            month_forecast=22000.0,
            month_confidence=80.0,
            week_method="combined",
            month_method="combined",
            last_4_weeks_avg=5000.0,
            last_3_months_avg=20000.0,
            growth_trend=10.5,
        )
    )
    return metrics


@pytest.fixture
def getter(mock_payment_metrics):
    """Создаёт PaymentStatsGetter с мокнутым сервисом."""
    return PaymentStatsGetter(payment_metrics=mock_payment_metrics)


# ============================================================================
# Тесты базовой функциональности
# ============================================================================


class TestPaymentStatsGetterBasic:
    """Тесты базовой функциональности PaymentStatsGetter."""

    @pytest.mark.asyncio
    async def test_get_data_returns_dict(self, getter, mock_dialog_manager):
        """get_data() возвращает dict с PAYMENT_STATS_MSG."""
        result = await getter.get_data(mock_dialog_manager)

        assert isinstance(result, dict)
        assert "PAYMENT_STATS_MSG" in result

    @pytest.mark.asyncio
    async def test_get_data_message_is_string(self, getter, mock_dialog_manager):
        """PAYMENT_STATS_MSG — строка."""
        result = await getter.get_data(mock_dialog_manager)

        assert isinstance(result["PAYMENT_STATS_MSG"], str)

    @pytest.mark.asyncio
    async def test_get_data_contains_revenue_info(self, getter, mock_dialog_manager):
        """Сообщение содержит информацию о выручке."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # Формат: 100,000.00 (с запятой как разделителем тысяч)
        assert "100,000.00" in msg  # Year total
        assert "15,000.00" in msg  # Month total
        assert "5,000.00" in msg  # Week total
        assert "1,500.00" in msg  # Day total


class TestPaymentStatsGetterDialogData:
    """Тесты сохранения данных в dialog_data."""

    @pytest.mark.asyncio
    async def test_saves_revenue_stats(
        self, getter, mock_dialog_manager
    ):
        """Сохраняет revenue_stats в dialog_data."""
        await getter.get_data(mock_dialog_manager)

        assert "revenue_stats" in mock_dialog_manager.dialog_data
        revenue_stats = mock_dialog_manager.dialog_data["revenue_stats"]

        assert revenue_stats["year_total"] == 100000.0
        assert revenue_stats["month_total"] == 15000.0
        assert revenue_stats["week_total"] == 5000.0
        assert revenue_stats["day_total"] == 1500.0

    @pytest.mark.asyncio
    async def test_saves_forecast(self, getter, mock_dialog_manager):
        """Сохраняет forecast в dialog_data."""
        await getter.get_data(mock_dialog_manager)

        assert "forecast" in mock_dialog_manager.dialog_data
        forecast = mock_dialog_manager.dialog_data["forecast"]

        assert forecast["week_forecast"] == 5500.0
        assert forecast["month_forecast"] == 22000.0
        assert forecast["growth_trend"] == 10.5

    @pytest.mark.asyncio
    async def test_saves_last_updated(self, getter, mock_dialog_manager):
        """Сохраняет last_updated в dialog_data."""
        await getter.get_data(mock_dialog_manager)

        assert "last_updated" in mock_dialog_manager.dialog_data
        assert isinstance(mock_dialog_manager.dialog_data["last_updated"], str)


class TestPaymentStatsGetterForecast:
    """Тесты прогнозирования."""

    @pytest.mark.asyncio
    async def test_forecast_in_message(self, getter, mock_dialog_manager):
        """Прогноз включён в сообщение."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # Формат: 5,500.00 (с запятой как разделителем тысяч)
        assert "5,500.00" in msg  # Week forecast
        assert "22,000.00" in msg  # Month forecast
        assert "75%" in msg  # Week confidence
        assert "80%" in msg  # Month confidence

    @pytest.mark.asyncio
    async def test_growth_trend_in_message(self, getter, mock_dialog_manager):
        """Тренд роста включён в сообщение."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        assert "10.5%" in msg or "+10.5" in msg


class TestPaymentStatsGetterErrors:
    """Тесты обработки ошибок."""

    @pytest.mark.asyncio
    async def test_revenue_stats_error(self, mock_dialog_manager):
        """Ошибка при получении статистики выручки."""
        mock_metrics = AsyncMock()
        mock_metrics.get_revenue_stats = AsyncMock(
            side_effect=Exception("DB connection failed")
        )

        getter = PaymentStatsGetter(payment_metrics=mock_metrics)
        result = await getter.get_data(mock_dialog_manager)

        assert "PAYMENT_STATS_MSG" in result
        assert "❌ Ошибка" in result["PAYMENT_STATS_MSG"]
        assert "DB connection failed" in result["PAYMENT_STATS_MSG"]

    @pytest.mark.asyncio
    async def test_forecast_error(self, mock_dialog_manager):
        """Ошибка при получении прогноза."""
        mock_metrics = AsyncMock()
        mock_metrics.get_revenue_stats = AsyncMock(
            return_value=RevenueStats()
        )
        mock_metrics.forecast_revenue = AsyncMock(
            side_effect=Exception("Forecast failed")
        )

        getter = PaymentStatsGetter(payment_metrics=mock_metrics)
        result = await getter.get_data(mock_dialog_manager)

        assert "PAYMENT_STATS_MSG" in result
        assert "❌ Ошибка" in result["PAYMENT_STATS_MSG"]


class TestPaymentStatsGetterFormatting:
    """Тесты форматирования сообщения."""

    @pytest.mark.asyncio
    async def test_message_contains_emoji(self, getter, mock_dialog_manager):
        """Сообщение содержит эмодзи."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        assert "💰" in msg  # Title
        assert "📊" in msg  # Stats section
        assert "🔮" in msg  # Forecast section

    @pytest.mark.asyncio
    async def test_message_contains_confidence_emoji(
        self, getter, mock_dialog_manager
    ):
        """Сообщение содержит эмодзи уверенности прогноза."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # 75% и 80% — это > 70%, должен быть 🟢
        assert "🟢" in msg

    @pytest.mark.asyncio
    async def test_message_contains_growth_indicator(
        self, getter, mock_dialog_manager
    ):
        """Сообщение содержит индикатор роста."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # Положительный тренд — 📈
        assert "📈" in msg

    @pytest.mark.asyncio
    async def test_message_contains_reference_data(
        self, getter, mock_dialog_manager
    ):
        """Сообщение содержит справочные данные."""
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        assert "Среднее за 4 недели" in msg
        assert "Среднее за 3 месяца" in msg


class TestPaymentStatsGetterLowConfidence:
    """Тесты низкой уверенности прогноза."""

    @pytest.mark.asyncio
    async def test_low_confidence_emoji(self, mock_dialog_manager):
        """Низкая уверенность — красный эмодзи."""
        mock_metrics = AsyncMock()
        mock_metrics.get_revenue_stats = AsyncMock(return_value=RevenueStats())
        mock_metrics.forecast_revenue = AsyncMock(
            return_value=RevenueForecast(
                week_forecast=1000.0,
                week_confidence=25.0,  # < 40%
                month_forecast=5000.0,
                month_confidence=30.0,  # < 40%
                week_method="combined",
                month_method="combined",
            )
        )

        getter = PaymentStatsGetter(payment_metrics=mock_metrics)
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # < 40% — должен быть 🔴
        assert "🔴" in msg

    @pytest.mark.asyncio
    async def test_medium_confidence_emoji(self, mock_dialog_manager):
        """Средняя уверенность — жёлтый эмодзи."""
        mock_metrics = AsyncMock()
        mock_metrics.get_revenue_stats = AsyncMock(return_value=RevenueStats())
        mock_metrics.forecast_revenue = AsyncMock(
            return_value=RevenueForecast(
                week_forecast=1000.0,
                week_confidence=50.0,  # 40-70%
                month_forecast=5000.0,
                month_confidence=60.0,  # 40-70%
                week_method="combined",
                month_method="combined",
            )
        )

        getter = PaymentStatsGetter(payment_metrics=mock_metrics)
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        # 40-70% — должен быть 🟡
        assert "🟡" in msg


class TestPaymentStatsGetterNoForecast:
    """Тесты отсутствия прогноза."""

    @pytest.mark.asyncio
    async def test_no_forecast_message(self, mock_dialog_manager):
        """Сообщение при отсутствии прогноза."""
        mock_metrics = AsyncMock()
        mock_metrics.get_revenue_stats = AsyncMock(return_value=RevenueStats())
        mock_metrics.forecast_revenue = AsyncMock(
            return_value=RevenueForecast()  # Все нули
        )

        getter = PaymentStatsGetter(payment_metrics=mock_metrics)
        result = await getter.get_data(mock_dialog_manager)
        msg = result["PAYMENT_STATS_MSG"]

        assert "Недостаточно данных" in msg
