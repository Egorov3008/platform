"""Тесты для ChurnMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from services.analytics.churn_metrics import (
    ChurnMetrics,
    ChurnMetricsService,
    ChurnCohort,
    ChurnPeriodMetrics,
    ActiveUsersTrend,
)


class TestChurnMetricsDataclass:
    """Тесты для dataclass ChurnMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = ChurnMetrics()
        assert metrics.churn_30d is None
        assert metrics.churn_60d is None
        assert metrics.churn_90d is None
        assert metrics.cohorts == []
        assert metrics.active_trend == []
        assert metrics.overall_churn_rate == 0.0
        assert metrics.overall_retention_rate == 0.0
        assert metrics.total_users == 0
        assert metrics.total_active == 0

    def test_with_values(self):
        """Инициализация со значениями."""
        metrics = ChurnMetrics(
            churn_30d=ChurnPeriodMetrics(
                period_days=30,
                total_users=100,
                active_users=80,
                churned_users=20,
                churn_rate=20.0,
                retention_rate=80.0,
            ),
            overall_churn_rate=20.0,
            overall_retention_rate=80.0,
            total_users=100,
            total_active=80,
        )
        assert metrics.churn_30d.period_days == 30
        assert metrics.churn_30d.churn_rate == 20.0
        assert metrics.overall_churn_rate == 20.0


class TestChurnMetricsService:
    """Тесты для ChurnMetricsService."""

    @pytest.fixture
    def mock_pool(self):
        """Создаёт mock пул соединений с правильным async context manager."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def service(self, mock_pool):
        """Создаёт сервис с mock пулом."""
        pool, _ = mock_pool
        return ChurnMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_churn_metrics(self, service, mock_pool):
        """get_all_churn_metrics() возвращает ChurnMetrics."""
        pool, mock_conn = mock_pool

        # Mock для churn по периодам
        period_row = {
            "total_users": 100,
            "active_users": 80,
            "churned_users": 20,
            "churn_rate": 20.0,
        }

        # Mock для когорт
        cohort_rows = [
            {
                "cohort_month": datetime(2026, 3, 1),
                "total_users": 50,
                "retained_users": 40,
                "churned_users": 10,
                "churn_rate": 20.0,
                "retention_rate": 80.0,
            }
        ]

        # Mock для тренда
        trend_rows = [
            {
                "date": datetime(2026, 3, 30),
                "active_users": 85,
                "new_users": 5,
                "churned_users": 0,
            }
        ]

        # Mock для общих метрик
        overall_row = {
            "total_users": 100,
            "total_active": 80,
        }

        mock_conn.fetchrow.side_effect = [period_row, period_row, period_row, overall_row]
        mock_conn.fetch.side_effect = [cohort_rows, trend_rows]

        metrics = await service.get_all_churn_metrics()

        assert isinstance(metrics, ChurnMetrics)
        assert metrics.churn_30d is not None
        assert metrics.churn_30d.period_days == 30
        assert metrics.churn_30d.churn_rate == 20.0
        assert len(metrics.cohorts) == 1
        assert len(metrics.active_trend) == 1

    @pytest.mark.asyncio
    async def test_get_all_churn_metrics_empty_db(self, service, mock_pool):
        """get_all_churn_metrics() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        empty_period = {
            "total_users": 0,
            "active_users": 0,
            "churned_users": 0,
            "churn_rate": 0.0,
        }

        mock_conn.fetchrow.side_effect = [
            empty_period, empty_period, empty_period,
            {"total_users": 0, "total_active": 0}
        ]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_churn_metrics()

        assert isinstance(metrics, ChurnMetrics)
        assert metrics.churn_30d is not None
        assert metrics.churn_30d.total_users == 0
        assert metrics.cohorts == []
        assert metrics.overall_churn_rate == 0.0

    @pytest.mark.asyncio
    async def test_churn_rate_calculation(self, service, mock_pool):
        """Процент оттока рассчитывается корректно."""
        pool, mock_conn = mock_pool

        period_row = {
            "total_users": 100,
            "active_users": 75,
            "churned_users": 25,
            "churn_rate": 25.0,
        }

        mock_conn.fetchrow.side_effect = [
            period_row, period_row, period_row,
            {"total_users": 100, "total_active": 75}
        ]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_churn_metrics()

        assert metrics.churn_30d.churn_rate == 25.0
        assert metrics.churn_30d.retention_rate == 75.0
        assert metrics.churn_30d.churned_users == 25


class TestChurnMetricsServiceCaching:
    """Тесты для кэширования Churn-метрик."""

    @pytest.fixture
    def mock_pool(self):
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def mock_cache_service(self):
        cache_service = MagicMock()
        cache_service.storage = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_get_cached_returns_from_cache(self, mock_pool, mock_cache_service):
        """get_cached() возвращает данные из кэша если есть."""
        pool, _ = mock_pool
        service = ChurnMetricsService(pool)

        cached_data = {
            "churn_30d": {
                "period_days": 30,
                "total_users": 100,
                "active_users": 80,
                "churned_users": 20,
                "churn_rate": 20.0,
                "retention_rate": 80.0,
            },
            "churn_60d": None,
            "churn_90d": None,
            "cohorts": [],
            "active_trend": [],
            "overall_churn_rate": 20.0,
            "overall_retention_rate": 80.0,
            "total_users": 100,
            "total_active": 80,
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, ChurnMetrics)
        assert metrics.churn_30d.total_users == 100
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = ChurnMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        empty_period = {
            "total_users": 0,
            "active_users": 0,
            "churned_users": 0,
            "churn_rate": 0.0,
        }

        mock_conn.fetchrow.side_effect = [
            empty_period, empty_period, empty_period,
            {"total_users": 0, "total_active": 0}
        ]
        mock_conn.fetch.return_value = []

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert isinstance(metrics, ChurnMetrics)
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"  # namespace
        assert call_args[1] == "churn_metrics"  # key


class TestMetricsSerialization:
    """Тесты сериализации/десериализации ChurnMetrics."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = ChurnMetrics(
            churn_30d=ChurnPeriodMetrics(
                period_days=30,
                total_users=100,
                active_users=80,
                churned_users=20,
                churn_rate=20.0,
                retention_rate=80.0,
            ),
            churn_60d=ChurnPeriodMetrics(
                period_days=60,
                total_users=150,
                active_users=120,
                churned_users=30,
                churn_rate=20.0,
                retention_rate=80.0,
            ),
            cohorts=[
                ChurnCohort(
                    cohort_month=datetime(2026, 3, 1),
                    total_users=50,
                    retained_users=40,
                    churned_users=10,
                    churn_rate=20.0,
                    retention_rate=80.0,
                )
            ],
            active_trend=[
                ActiveUsersTrend(
                    date=datetime(2026, 3, 30),
                    active_users=85,
                    new_users=5,
                    churned_users=0,
                )
            ],
            overall_churn_rate=20.0,
            overall_retention_rate=80.0,
            total_users=100,
            total_active=80,
        )

        data = ChurnMetricsService._metrics_to_dict(metrics)

        assert data["churn_30d"]["period_days"] == 30
        assert data["churn_60d"]["period_days"] == 60
        assert len(data["cohorts"]) == 1
        assert len(data["active_trend"]) == 1
        assert data["overall_churn_rate"] == 20.0

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "churn_30d": {
                "period_days": 30,
                "total_users": 100,
                "active_users": 80,
                "churned_users": 20,
                "churn_rate": 20.0,
                "retention_rate": 80.0,
            },
            "churn_60d": None,
            "churn_90d": None,
            "cohorts": [
                {
                    "cohort_month": "2026-03-01T00:00:00",
                    "total_users": 50,
                    "retained_users": 40,
                    "churned_users": 10,
                    "churn_rate": 20.0,
                    "retention_rate": 80.0,
                }
            ],
            "active_trend": [
                {
                    "date": "2026-03-30T00:00:00",
                    "active_users": 85,
                    "new_users": 5,
                    "churned_users": 0,
                }
            ],
            "overall_churn_rate": 20.0,
            "overall_retention_rate": 80.0,
            "total_users": 100,
            "total_active": 80,
        }

        metrics = ChurnMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, ChurnMetrics)
        assert metrics.churn_30d.total_users == 100
        assert metrics.churn_60d is None
        assert len(metrics.cohorts) == 1
        assert len(metrics.active_trend) == 1

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = ChurnMetrics(
            churn_30d=ChurnPeriodMetrics(
                period_days=30,
                total_users=100,
                active_users=80,
                churned_users=20,
                churn_rate=20.0,
                retention_rate=80.0,
            ),
            overall_churn_rate=20.0,
            overall_retention_rate=80.0,
            total_users=100,
            total_active=80,
        )

        data = ChurnMetricsService._metrics_to_dict(original)
        restored = ChurnMetricsService._dict_to_metrics(data)

        assert restored.churn_30d.total_users == original.churn_30d.total_users
        assert restored.overall_churn_rate == original.overall_churn_rate
        assert restored.total_users == original.total_users
