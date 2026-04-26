"""Тесты для PaymentMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from services.analytics.payment_metrics import (
    PaymentMetricsService,
    RevenueStats,
    RevenueForecast,
    WeeklyRevenue,
    MonthlyRevenue,
)


class TestRevenueStatsDataclass:
    """Тесты для dataclass RevenueStats."""

    def test_default_values(self):
        """Значения по умолчанию."""
        stats = RevenueStats()
        assert stats.year_total == 0.0
        assert stats.month_total == 0.0
        assert stats.week_total == 0.0
        assert stats.day_total == 0.0
        assert stats.year_payments_count == 0
        assert stats.month_payments_count == 0
        assert stats.week_payments_count == 0
        assert stats.day_payments_count == 0
        assert stats.avg_payment_year == 0.0
        assert stats.avg_payment_month == 0.0
        assert stats.avg_payment_week == 0.0
        assert stats.avg_payment_day == 0.0

    def test_with_values(self):
        """Инициализация со значениями."""
        stats = RevenueStats(
            year_total=100000.0,
            month_total=15000.0,
            week_total=5000.0,
            year_payments_count=50,
            month_payments_count=10,
            week_payments_count=3,
        )
        assert stats.year_total == 100000.0
        assert stats.week_payments_count == 3


class TestRevenueForecastDataclass:
    """Тесты для dataclass RevenueForecast."""

    def test_default_values(self):
        """Значения по умолчанию."""
        forecast = RevenueForecast()
        assert forecast.week_forecast == 0.0
        assert forecast.week_confidence == 0.0
        assert forecast.month_forecast == 0.0
        assert forecast.month_confidence == 0.0
        assert forecast.week_method == "none"
        assert forecast.month_method == "none"
        assert forecast.growth_trend == 0.0

    def test_with_values(self):
        """Инициализация со значениями."""
        forecast = RevenueForecast(
            week_forecast=5000.0,
            week_confidence=75.0,
            month_forecast=20000.0,
            month_confidence=80.0,
            week_method="combined",
            month_method="combined",
            growth_trend=10.5,
        )
        assert forecast.week_forecast == 5000.0
        assert forecast.growth_trend == 10.5


class TestPaymentMetricsService:
    """Тесты для PaymentMetricsService."""

    @pytest.fixture
    def mock_pool(self):
        """Создаёт mock пула соединений с правильным async context manager."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def service(self, mock_pool):
        """Создаёт сервис с mock пулом."""
        pool, _ = mock_pool
        return PaymentMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_revenue_stats(self, service, mock_pool):
        """get_revenue_stats() возвращает RevenueStats."""
        pool, mock_conn = mock_pool

        # Mock для запроса за год
        year_row = {"total": 100000.0, "count": 50}
        # Mock для запроса за месяц
        month_row = {"total": 15000.0, "count": 10}
        # Mock для запроса за неделю
        week_row = {"total": 5000.0, "count": 3}
        # Mock для запроса за день
        day_row = {"total": 1500.0, "count": 1}

        mock_conn.fetchrow = AsyncMock(side_effect=[year_row, month_row, week_row, day_row])

        stats = await service.get_revenue_stats()

        assert isinstance(stats, RevenueStats)
        assert stats.year_total == 100000.0
        assert stats.month_total == 15000.0
        assert stats.week_total == 5000.0
        assert stats.day_total == 1500.0
        assert stats.year_payments_count == 50
        assert stats.month_payments_count == 10
        assert stats.week_payments_count == 3
        assert stats.day_payments_count == 1
        # Средний чек
        assert stats.avg_payment_year == 2000.0  # 100000 / 50
        assert stats.avg_payment_month == 1500.0  # 15000 / 10
        assert abs(stats.avg_payment_week - 1666.67) < 1  # 5000 / 3
        assert stats.avg_payment_day == 1500.0  # 1500 / 1

    @pytest.mark.asyncio
    async def test_get_revenue_stats_empty_db(self, service, mock_pool):
        """get_revenue_stats() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        empty_row = {"total": 0.0, "count": 0}
        mock_conn.fetchrow = AsyncMock(return_value=empty_row)

        stats = await service.get_revenue_stats()

        assert isinstance(stats, RevenueStats)
        assert stats.year_total == 0.0
        assert stats.month_total == 0.0
        assert stats.week_total == 0.0
        assert stats.day_total == 0.0
        assert stats.avg_payment_year == 0.0
        assert stats.avg_payment_day == 0.0

    @pytest.mark.asyncio
    async def test_forecast_revenue(self, service, mock_pool):
        """forecast_revenue() возвращает RevenueForecast."""
        pool, mock_conn = mock_pool

        # Mock для weekly data (8 недель)
        now = datetime.now(timezone.utc)
        weekly_rows = [
            {
                "week_start": now - timedelta(weeks=i),
                "week_end": now - timedelta(weeks=i - 1),
                "total": 5000.0 + i * 100,  # Растущий тренд
                "payments_count": 5 + i,
            }
            for i in range(8)
        ]

        # Mock для monthly data (6 месяцев)
        monthly_rows = [
            {
                "month_start": now - timedelta(days=30 * i),
                "month_end": now - timedelta(days=30 * (i - 1)),
                "total": 20000.0 + i * 500,
                "payments_count": 20 + i * 2,
            }
            for i in range(6)
        ]

        mock_conn.fetch = AsyncMock(side_effect=[weekly_rows, monthly_rows])

        forecast = await service.forecast_revenue()

        assert isinstance(forecast, RevenueForecast)
        assert forecast.week_forecast > 0
        assert forecast.month_forecast > 0
        assert forecast.week_confidence > 0
        assert forecast.month_confidence > 0
        assert forecast.week_method == "combined"
        assert forecast.month_method == "combined"
        assert forecast.last_4_weeks_avg > 0
        assert forecast.last_3_months_avg > 0

    @pytest.mark.asyncio
    async def test_forecast_revenue_no_data(self, service, mock_pool):
        """forecast_revenue() возвращает пустой прогноз без данных."""
        pool, mock_conn = mock_pool

        mock_conn.fetch = AsyncMock(return_value=[])

        forecast = await service.forecast_revenue()

        assert isinstance(forecast, RevenueForecast)
        assert forecast.week_forecast == 0.0
        assert forecast.month_forecast == 0.0
        assert forecast.week_method == "none"
        assert forecast.month_method == "none"


class TestPaymentMetricsServiceForecasting:
    """Тесты алгоритмов прогнозирования."""

    @pytest.fixture
    def mock_pool(self):
        """Создаёт mock пула."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def service(self, mock_pool):
        """Создаёт сервис."""
        pool, _ = mock_pool
        return PaymentMetricsService(pool)

    def test_linear_regression_increasing(self, service):
        """Линейная регрессия для растущих данных."""
        values = [1000, 2000, 3000, 4000, 5000]
        slope, intercept = service._linear_regression(values)

        # slope должен быть положительным
        assert slope > 0
        # Ожидаемый slope ≈ 1000
        assert abs(slope - 1000) < 100

    def test_linear_regression_constant(self, service):
        """Линейная регрессия для постоянных данных."""
        values = [5000, 5000, 5000, 5000, 5000]
        slope, intercept = service._linear_regression(values)

        # slope должен быть близок к 0
        assert abs(slope) < 0.01
        # intercept ≈ 5000
        assert abs(intercept - 5000) < 0.01

    def test_forecast_single_value(self, service):
        """Прогноз одного значения."""
        # Данные за последние 8 недель (растущий тренд)
        now = datetime.now(timezone.utc)
        data_points = [
            WeeklyRevenue(
                week_start=now - timedelta(weeks=i),
                week_end=now,
                total=5000.0 + (7 - i) * 200,
                payments_count=5,
            )
            for i in range(8)
        ]

        forecast, confidence, method = service._forecast_single_value(
            data_points, "week"
        )

        assert forecast > 0
        assert 10 <= confidence <= 95
        assert method == "combined"

    def test_calculate_confidence_stable_data(self, service):
        """Уверенность для стабильных данных должна быть высокой."""
        values = [5000, 5100, 4900, 5050, 4950, 5000, 5100, 4900]
        confidence = service._calculate_confidence(values)

        # Для стабильных данных уверенность должна быть относительно высокой
        assert confidence > 50

    def test_calculate_confidence_volatile_data(self, service):
        """Уверенность для волатильных данных должна быть ниже, чем для стабильных."""
        volatile_values = [1000, 9000, 2000, 8000, 3000, 7000, 4000, 6000]
        stable_values = [5000, 5100, 4900, 5050, 4950, 5000, 5100, 4900]

        volatile_confidence = service._calculate_confidence(volatile_values)
        stable_confidence = service._calculate_confidence(stable_values)

        # Уверенность для волатильных данных должна быть ниже, чем для стабильных
        assert volatile_confidence < stable_confidence

    def test_calculate_growth_trend_positive(self, service):
        """Расчёт тренда роста для положительных данных."""
        now = datetime.now(timezone.utc)
        weekly_data = [
            WeeklyRevenue(
                week_start=now - timedelta(weeks=i),
                week_end=now,
                total=6000.0 - i * 200,  # Последние недели больше
                payments_count=5,
            )
            for i in range(8)
        ]

        monthly_data = []

        trend = service._calculate_growth_trend(weekly_data, monthly_data)

        # Тренд должен быть положительным
        assert trend > 0

    def test_calculate_growth_trend_no_data(self, service):
        """Расчёт тренда без данных."""
        trend = service._calculate_growth_trend([], [])
        assert trend == 0.0


class TestPaymentMetricsServiceCaching:
    """Тесты корректности работы с БД."""

    @pytest.fixture
    def mock_pool(self):
        """Создаёт mock пула."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def service(self, mock_pool):
        """Создаёт сервис."""
        pool, _ = mock_pool
        return PaymentMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_weekly_revenue_query(self, service, mock_pool):
        """_get_weekly_revenue() выполняет корректный запрос."""
        pool, mock_conn = mock_pool

        now = datetime.now(timezone.utc)
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "week_start": now - timedelta(weeks=1),
                    "week_end": now,
                    "total": 5000.0,
                    "payments_count": 5,
                }
            ]
        )

        async with pool.acquire() as conn:
            result = await service._get_weekly_revenue(conn, weeks=8)

        assert len(result) == 1
        assert isinstance(result[0], WeeklyRevenue)
        assert result[0].total == 5000.0
        assert result[0].payments_count == 5

    @pytest.mark.asyncio
    async def test_get_monthly_revenue_query(self, service, mock_pool):
        """_get_monthly_revenue() выполняет корректный запрос."""
        pool, mock_conn = mock_pool

        now = datetime.now(timezone.utc)
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "month_start": now - timedelta(days=30),
                    "month_end": now,
                    "total": 20000.0,
                    "payments_count": 20,
                }
            ]
        )

        async with pool.acquire() as conn:
            result = await service._get_monthly_revenue(conn, months=6)

        assert len(result) == 1
        assert isinstance(result[0], MonthlyRevenue)
        assert result[0].total == 20000.0
        assert result[0].payments_count == 20
