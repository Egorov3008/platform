"""Тесты для DashboardMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from services.analytics.dashboard_metrics import (
    DashboardMetrics,
    DashboardMetricsService,
    MRRMetrics,
    FunnelMetrics,
    KeyExpiryMetrics,
    PaymentStatusMetrics,
)


class TestDashboardMetricsDataclass:
    """Тесты для dataclass DashboardMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = DashboardMetrics()
        assert metrics.mrr_current_month == 0.0
        assert metrics.mrr_previous_month == 0.0
        assert metrics.mrr_growth == 0.0
        assert metrics.paying_users_current == 0
        assert metrics.arpu_current == 0.0
        assert metrics.funnel == []
        assert metrics.expiring_keys == []
        assert metrics.payment_statuses == []

    def test_with_values(self):
        """Инициализация со значениями."""
        metrics = DashboardMetrics(
            mrr_current_month=5000.0,
            mrr_previous_month=4000.0,
            mrr_growth=25.0,
            paying_users_current=10,
            arpu_current=500.0,
            total_new_users_30d=100,
            total_expiring_72h=5,
            total_succeeded=50,
            succeeded_pct=80.0,
        )
        assert metrics.mrr_current_month == 5000.0
        assert metrics.mrr_growth == 25.0
        assert metrics.total_new_users_30d == 100


class TestDashboardMetricsService:
    """Тесты для DashboardMetricsService."""

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
        return DashboardMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_dashboard_metrics(self, service, mock_pool):
        """get_all_dashboard_metrics() возвращает DashboardMetrics."""
        pool, mock_conn = mock_pool

        # Mock для MRR запроса
        mrr_rows = [
            {
                "month": datetime(2026, 3, 1),
                "revenue": 5000.0,
                "paying_users": 10,
                "arpu": 500.0,
            },
            {
                "month": datetime(2026, 2, 1),
                "revenue": 4000.0,
                "paying_users": 8,
                "arpu": 500.0,
            },
        ]

        # Mock для funnel запроса
        funnel_rows = [
            {
                "date": datetime(2026, 3, 1).date(),
                "new_users": 10,
                "users_with_keys": 8,
                "paying_users": 3,
            }
        ]

        # Mock для expiring keys запроса
        expiry_rows = [
            {"expiry_range": "Менее 24ч", "keys_count": 2},
            {"expiry_range": "24-48ч", "keys_count": 3},
        ]

        # Mock для payment statuses запроса
        payment_rows = [
            {"status": "succeeded", "count": 50, "total_amount": 5000.0},
            {"status": "pending", "count": 10, "total_amount": 1000.0},
        ]

        # Настраиваем последовательные вызовы fetch
        mock_conn.fetch.side_effect = [
            mrr_rows,  # MRR
            funnel_rows,  # Funnel
            expiry_rows,  # Expiring keys
            payment_rows,  # Payment statuses
        ]

        metrics = await service.get_all_dashboard_metrics()

        assert isinstance(metrics, DashboardMetrics)
        assert metrics.mrr_current_month == 5000.0
        assert metrics.mrr_previous_month == 4000.0
        assert metrics.mrr_growth == 25.0  # (5000-4000)/4000*100
        assert metrics.paying_users_current == 10
        assert metrics.arpu_current == 500.0

    @pytest.mark.asyncio
    async def test_get_all_dashboard_metrics_empty_db(self, service, mock_pool):
        """get_all_dashboard_metrics() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        # Все запросы возвращают пустые списки
        mock_conn.fetch.side_effect = [[], [], [], []]

        metrics = await service.get_all_dashboard_metrics()

        assert isinstance(metrics, DashboardMetrics)
        assert metrics.mrr_current_month == 0.0
        assert metrics.total_new_users_30d == 0
        assert metrics.total_expiring_72h == 0

    @pytest.mark.asyncio
    async def test_funnel_conversion_calculation(self, service, mock_pool):
        """Конверсии воронки рассчитываются корректно."""
        pool, mock_conn = mock_pool

        funnel_rows = [
            {
                "date": datetime(2026, 3, 1).date(),
                "new_users": 100,
                "users_with_keys": 50,
                "paying_users": 20,
            }
        ]

        mock_conn.fetch.side_effect = [
            [],  # MRR пустой
            funnel_rows,
            [],  # Expiring keys
            [],  # Payment statuses
        ]

        metrics = await service.get_all_dashboard_metrics()

        assert metrics.total_new_users_30d == 100
        assert metrics.total_users_with_keys_30d == 50
        assert metrics.total_paying_users_30d == 20
        assert metrics.conversion_to_keys_pct == 50.0  # 50/100*100
        assert metrics.conversion_to_paid_pct == 20.0  # 20/100*100

    @pytest.mark.asyncio
    async def test_expiring_keys_calculation(self, service, mock_pool):
        """Подсчёт истекающих ключей работает корректно."""
        pool, mock_conn = mock_pool

        expiry_rows = [
            {"expiry_range": "Менее 24ч", "keys_count": 5},
            {"expiry_range": "24-48ч", "keys_count": 10},
            {"expiry_range": "48-72ч", "keys_count": 15},
            {"expiry_range": "Более 72ч", "keys_count": 100},
        ]

        mock_conn.fetch.side_effect = [
            [],  # MRR
            [],  # Funnel
            expiry_rows,
            [],  # Payment statuses
        ]

        metrics = await service.get_all_dashboard_metrics()

        assert metrics.total_expiring_72h == 30  # 5+10+15 (Менее 24ч + 24-48ч + 48-72ч)
        assert len(metrics.expiring_keys) == 4


class TestDashboardMetricsServiceCaching:
    """Тесты для кэширования dashboard-метрик."""

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
        service = DashboardMetricsService(pool)

        cached_data = {
            "mrr_current_month": 5000.0,
            "mrr_previous_month": 4000.0,
            "mrr_growth": 25.0,
            "paying_users_current": 10,
            "arpu_current": 500.0,
            "funnel": [],
            "total_new_users_30d": 100,
            "total_users_with_keys_30d": 50,
            "total_paying_users_30d": 20,
            "conversion_to_keys_pct": 50.0,
            "conversion_to_paid_pct": 20.0,
            "expiring_keys": [],
            "total_expiring_72h": 0,
            "payment_statuses": [],
            "total_succeeded": 50,
            "total_pending": 10,
            "total_canceled": 0,
            "succeeded_pct": 83.3,
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, DashboardMetrics)
        assert metrics.mrr_current_month == 5000.0
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = DashboardMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        # Mock для всех запросов
        mock_conn.fetch.side_effect = [
            [],  # MRR
            [],  # Funnel
            [],  # Expiring keys
            [],  # Payment statuses
        ]

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert isinstance(metrics, DashboardMetrics)
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"  # namespace
        assert call_args[1] == "dashboard_metrics"  # key


class TestMetricsSerialization:
    """Тесты сериализации/десериализации DashboardMetrics."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = DashboardMetrics(
            mrr_current_month=5000.0,
            mrr_previous_month=4000.0,
            mrr_growth=25.0,
            paying_users_current=10,
            arpu_current=500.0,
            funnel=[
                FunnelMetrics(
                    date=datetime(2026, 3, 1),
                    new_users=100,
                    users_with_keys=50,
                    paying_users=20,
                )
            ],
            total_new_users_30d=100,
            total_users_with_keys_30d=50,
            total_paying_users_30d=20,
            conversion_to_keys_pct=50.0,
            conversion_to_paid_pct=20.0,
            expiring_keys=[
                KeyExpiryMetrics(expiry_range="Менее 24ч", keys_count=5),
                KeyExpiryMetrics(expiry_range="24-48ч", keys_count=10),
            ],
            total_expiring_72h=15,
            payment_statuses=[
                PaymentStatusMetrics(status="succeeded", count=50, total_amount=5000.0),
                PaymentStatusMetrics(status="pending", count=10, total_amount=1000.0),
            ],
            total_succeeded=50,
            total_pending=10,
            total_canceled=0,
            succeeded_pct=83.3,
        )

        data = DashboardMetricsService._metrics_to_dict(metrics)

        assert data["mrr_current_month"] == 5000.0
        assert data["mrr_growth"] == 25.0
        assert len(data["funnel"]) == 1
        assert len(data["expiring_keys"]) == 2
        assert data["total_expiring_72h"] == 15

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "mrr_current_month": 5000.0,
            "mrr_previous_month": 4000.0,
            "mrr_growth": 25.0,
            "paying_users_current": 10,
            "arpu_current": 500.0,
            "funnel": [
                {
                    "date": "2026-03-01T00:00:00",
                    "new_users": 100,
                    "users_with_keys": 50,
                    "paying_users": 20,
                }
            ],
            "total_new_users_30d": 100,
            "total_users_with_keys_30d": 50,
            "total_paying_users_30d": 20,
            "conversion_to_keys_pct": 50.0,
            "conversion_to_paid_pct": 20.0,
            "expiring_keys": [
                {"expiry_range": "Менее 24ч", "keys_count": 5},
                {"expiry_range": "24-48ч", "keys_count": 10},
            ],
            "total_expiring_72h": 15,
            "payment_statuses": [
                {"status": "succeeded", "count": 50, "total_amount": 5000.0},
                {"status": "pending", "count": 10, "total_amount": 1000.0},
            ],
            "total_succeeded": 50,
            "total_pending": 10,
            "total_canceled": 0,
            "succeeded_pct": 83.3,
        }

        metrics = DashboardMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, DashboardMetrics)
        assert metrics.mrr_current_month == 5000.0
        assert len(metrics.funnel) == 1
        assert len(metrics.expiring_keys) == 2
        assert metrics.total_expiring_72h == 15

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = DashboardMetrics(
            mrr_current_month=5000.0,
            mrr_previous_month=4000.0,
            mrr_growth=25.0,
            paying_users_current=10,
            arpu_current=500.0,
            total_new_users_30d=100,
            total_expiring_72h=15,
            total_succeeded=50,
            succeeded_pct=83.3,
        )

        data = DashboardMetricsService._metrics_to_dict(original)
        restored = DashboardMetricsService._dict_to_metrics(data)

        assert restored.mrr_current_month == original.mrr_current_month
        assert restored.mrr_growth == original.mrr_growth
        assert restored.total_expiring_72h == original.total_expiring_72h
