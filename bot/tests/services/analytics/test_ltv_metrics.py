"""Тесты для LtvMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from services.analytics.ltv_metrics import (
    LtvMetrics,
    LtvMetricsService,
    LtvCohort,
    LtvDynamics,
)


class TestLtvMetricsDataclass:
    """Тесты для dataclass LtvMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = LtvMetrics()
        assert metrics.cohorts == []
        assert metrics.total_users == 0
        assert metrics.total_revenue == 0.0
        assert metrics.overall_avg_ltv == 0.0
        assert metrics.dynamics == []
        assert metrics.one_time_users == 0
        assert metrics.repeat_users == 0
        assert metrics.retention_rate == 0.0

    def test_with_values(self):
        """Инициализация со значениями."""
        metrics = LtvMetrics(
            cohorts=[
                LtvCohort(
                    cohort_name="1 платеж",
                    users_count=50,
                    avg_ltv=500.0,
                    min_ltv=100.0,
                    max_ltv=1000.0,
                    total_revenue=25000.0,
                )
            ],
            total_users=100,
            total_revenue=100000.0,
            overall_avg_ltv=1000.0,
            one_time_users=50,
            repeat_users=50,
            retention_rate=50.0,
        )
        assert len(metrics.cohorts) == 1
        assert metrics.total_users == 100
        assert metrics.overall_avg_ltv == 1000.0


class TestLtvMetricsService:
    """Тесты для LtvMetricsService."""

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
        return LtvMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_ltv_metrics(self, service, mock_pool):
        """get_all_ltv_metrics() возвращает LtvMetrics."""
        pool, mock_conn = mock_pool

        # Mock для LTV по когортам
        cohort_rows = [
            {
                "cohort_name": "1 платеж",
                "users_count": 50,
                "avg_ltv": 500.0,
                "min_ltv": 100.0,
                "max_ltv": 1000.0,
                "total_revenue": 25000.0,
            },
            {
                "cohort_name": "2-3 платежа",
                "users_count": 30,
                "avg_ltv": 1200.0,
                "min_ltv": 200.0,
                "max_ltv": 3000.0,
                "total_revenue": 36000.0,
            },
        ]

        # Mock для динамики LTV
        dynamics_rows = [
            {
                "month": datetime(2026, 3, 1),
                "paying_users": 20,
                "revenue": 10000.0,
                "arpu": 500.0,
            }
        ]

        # Mock для повторных платежей
        repeat_row = {
            "one_time_users": 50,
            "repeat_users": 50,
            "total_users": 100,
        }

        mock_conn.fetch.side_effect = [cohort_rows, dynamics_rows]
        mock_conn.fetchrow.return_value = repeat_row

        metrics = await service.get_all_ltv_metrics()

        assert isinstance(metrics, LtvMetrics)
        assert len(metrics.cohorts) == 2
        assert metrics.total_users == 80  # 50 + 30
        assert metrics.cohorts[0].cohort_name == "1 платеж"
        assert metrics.cohorts[0].users_count == 50

    @pytest.mark.asyncio
    async def test_get_all_ltv_metrics_empty_db(self, service, mock_pool):
        """get_all_ltv_metrics() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        mock_conn.fetch.return_value = []
        mock_conn.fetchrow.return_value = {
            "one_time_users": 0,
            "repeat_users": 0,
            "total_users": 0,
        }

        metrics = await service.get_all_ltv_metrics()

        assert isinstance(metrics, LtvMetrics)
        assert metrics.cohorts == []
        assert metrics.total_users == 0
        assert metrics.overall_avg_ltv == 0.0

    @pytest.mark.asyncio
    async def test_retention_rate_calculation(self, service, mock_pool):
        """Процент удержания рассчитывается корректно."""
        pool, mock_conn = mock_pool

        mock_conn.fetch.return_value = []
        mock_conn.fetchrow.return_value = {
            "one_time_users": 40,
            "repeat_users": 60,
            "total_users": 100,
        }

        metrics = await service.get_all_ltv_metrics()

        assert metrics.one_time_users == 40
        assert metrics.repeat_users == 60
        assert metrics.retention_rate == 60.0  # 60/100*100


class TestLtvMetricsServiceCaching:
    """Тесты для кэширования LTV-метрик."""

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
        service = LtvMetricsService(pool)

        cached_data = {
            "cohorts": [
                {
                    "cohort_name": "1 платеж",
                    "users_count": 50,
                    "avg_ltv": 500.0,
                    "min_ltv": 100.0,
                    "max_ltv": 1000.0,
                    "total_revenue": 25000.0,
                }
            ],
            "total_users": 50,
            "total_revenue": 25000.0,
            "overall_avg_ltv": 500.0,
            "dynamics": [],
            "one_time_users": 50,
            "repeat_users": 0,
            "retention_rate": 0.0,
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, LtvMetrics)
        assert metrics.total_users == 50
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = LtvMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        mock_conn.fetch.return_value = []
        mock_conn.fetchrow.return_value = {
            "one_time_users": 0,
            "repeat_users": 0,
            "total_users": 0,
        }

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert isinstance(metrics, LtvMetrics)
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"  # namespace
        assert call_args[1] == "ltv_metrics"  # key


class TestMetricsSerialization:
    """Тесты сериализации/десериализации LtvMetrics."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = LtvMetrics(
            cohorts=[
                LtvCohort(
                    cohort_name="1 платеж",
                    users_count=50,
                    avg_ltv=500.0,
                    min_ltv=100.0,
                    max_ltv=1000.0,
                    total_revenue=25000.0,
                ),
                LtvCohort(
                    cohort_name="2-3 платежа",
                    users_count=30,
                    avg_ltv=1200.0,
                    min_ltv=200.0,
                    max_ltv=3000.0,
                    total_revenue=36000.0,
                ),
            ],
            total_users=80,
            total_revenue=61000.0,
            overall_avg_ltv=762.5,
            dynamics=[
                LtvDynamics(
                    month=datetime(2026, 3, 1),
                    paying_users=20,
                    revenue=10000.0,
                    arpu=500.0,
                )
            ],
            one_time_users=50,
            repeat_users=30,
            retention_rate=37.5,
        )

        data = LtvMetricsService._metrics_to_dict(metrics)

        assert len(data["cohorts"]) == 2
        assert data["total_users"] == 80
        assert data["overall_avg_ltv"] == 762.5
        assert len(data["dynamics"]) == 1

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "cohorts": [
                {
                    "cohort_name": "1 платеж",
                    "users_count": 50,
                    "avg_ltv": 500.0,
                    "min_ltv": 100.0,
                    "max_ltv": 1000.0,
                    "total_revenue": 25000.0,
                }
            ],
            "total_users": 50,
            "total_revenue": 25000.0,
            "overall_avg_ltv": 500.0,
            "dynamics": [
                {
                    "month": "2026-03-01T00:00:00",
                    "paying_users": 20,
                    "revenue": 10000.0,
                    "arpu": 500.0,
                }
            ],
            "one_time_users": 50,
            "repeat_users": 0,
            "retention_rate": 0.0,
        }

        metrics = LtvMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, LtvMetrics)
        assert len(metrics.cohorts) == 1
        assert metrics.total_users == 50
        assert len(metrics.dynamics) == 1
        assert metrics.dynamics[0].paying_users == 20

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = LtvMetrics(
            cohorts=[
                LtvCohort(
                    cohort_name="1 платеж",
                    users_count=50,
                    avg_ltv=500.0,
                    min_ltv=100.0,
                    max_ltv=1000.0,
                    total_revenue=25000.0,
                )
            ],
            total_users=50,
            total_revenue=25000.0,
            overall_avg_ltv=500.0,
            one_time_users=50,
            repeat_users=0,
            retention_rate=0.0,
        )

        data = LtvMetricsService._metrics_to_dict(original)
        restored = LtvMetricsService._dict_to_metrics(data)

        assert restored.total_users == original.total_users
        assert restored.overall_avg_ltv == original.overall_avg_ltv
        assert len(restored.cohorts) == len(original.cohorts)
