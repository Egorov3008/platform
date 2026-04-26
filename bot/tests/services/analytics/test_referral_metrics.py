"""Тесты для ReferralMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from services.analytics.referral_metrics import (
    ReferralMetrics,
    ReferralMetricsService,
    ReferralOverview,
    TopReferrer,
    ReferralTariffStats,
)


class TestReferralMetricsDataclass:
    """Тесты для dataclass ReferralMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = ReferralMetrics()
        assert metrics.overview is None
        assert metrics.top_referrers == []
        assert metrics.tariff_stats == []
        assert metrics.total_revenue == 0.0
        assert metrics.avg_revenue_per_referrer == 0.0

    def test_with_values(self):
        """Инициализация со значениями."""
        metrics = ReferralMetrics(
            overview=ReferralOverview(
                total_referrers=10,
                total_referred=50,
                referred_with_keys=40,
                referred_paying=20,
                conversion_to_keys=80.0,
                conversion_to_paid=40.0,
            ),
            total_revenue=10000.0,
        )
        assert metrics.overview.total_referrers == 10
        assert metrics.overview.conversion_to_paid == 40.0
        assert metrics.total_revenue == 10000.0


class TestReferralMetricsService:
    """Тесты для ReferralMetricsService."""

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
        return ReferralMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_referral_metrics(self, service, mock_pool):
        """get_all_referral_metrics() возвращает ReferralMetrics."""
        pool, mock_conn = mock_pool

        # Mock для overview
        overview_row = {
            "total_referrers": 10,
            "total_referred": 50,
            "referred_with_keys": 40,
            "referred_paying": 20,
        }

        # Mock для топ рефереров
        top_referrers_rows = [
            {
                "referrer_tg_id": 123456,
                "referred_count": 15,
                "paying_referrals": 8,
                "total_revenue": 5000.0,
            }
        ]

        # Mock для тарифов
        tariff_rows = [
            {
                "tariff_name": "Premium",
                "referred_count": 30,
                "paying_count": 15,
                "total_revenue": 8000.0,
            }
        ]

        # Mock для total revenue
        revenue_row = {
            "total_revenue": 10000.0,
            "total_referrers": 10,
        }

        mock_conn.fetchrow.side_effect = [overview_row, revenue_row]
        mock_conn.fetch.side_effect = [top_referrers_rows, tariff_rows]

        metrics = await service.get_all_referral_metrics()

        assert isinstance(metrics, ReferralMetrics)
        assert metrics.overview is not None
        assert metrics.overview.total_referrers == 10
        assert len(metrics.top_referrers) == 1
        assert metrics.top_referrers[0].referred_count == 15
        assert len(metrics.tariff_stats) == 1

    @pytest.mark.asyncio
    async def test_get_all_referral_metrics_empty_db(self, service, mock_pool):
        """get_all_referral_metrics() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        overview_row = {
            "total_referrers": 0,
            "total_referred": 0,
            "referred_with_keys": 0,
            "referred_paying": 0,
        }

        mock_conn.fetchrow.side_effect = [overview_row, {"total_revenue": 0, "total_referrers": 0}]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_referral_metrics()

        assert isinstance(metrics, ReferralMetrics)
        assert metrics.overview is not None
        assert metrics.overview.total_referrers == 0
        assert metrics.top_referrers == []

    @pytest.mark.asyncio
    async def test_conversion_rate_calculation(self, service, mock_pool):
        """Проценты конверсии рассчитываются корректно."""
        pool, mock_conn = mock_pool

        overview_row = {
            "total_referrers": 10,
            "total_referred": 100,
            "referred_with_keys": 80,
            "referred_paying": 40,
        }

        mock_conn.fetchrow.side_effect = [
            overview_row,
            {"total_revenue": 0, "total_referrers": 10}
        ]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_referral_metrics()

        assert metrics.overview.conversion_to_keys == 80.0
        assert metrics.overview.conversion_to_paid == 40.0


class TestReferralMetricsServiceCaching:
    """Тесты для кэширования Referral-метрик."""

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
        service = ReferralMetricsService(pool)

        cached_data = {
            "overview": {
                "total_referrers": 10,
                "total_referred": 50,
                "referred_with_keys": 40,
                "referred_paying": 20,
                "conversion_to_keys": 80.0,
                "conversion_to_paid": 40.0,
            },
            "top_referrers": [],
            "tariff_stats": [],
            "total_revenue": 10000.0,
            "avg_revenue_per_referrer": 1000.0,
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, ReferralMetrics)
        assert metrics.overview.total_referrers == 10
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = ReferralMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        overview_row = {
            "total_referrers": 0,
            "total_referred": 0,
            "referred_with_keys": 0,
            "referred_paying": 0,
        }

        mock_conn.fetchrow.side_effect = [
            overview_row,
            {"total_revenue": 0, "total_referrers": 0}
        ]
        mock_conn.fetch.return_value = []

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert isinstance(metrics, ReferralMetrics)
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"
        assert call_args[1] == "referral_metrics"


class TestMetricsSerialization:
    """Тесты сериализации/десериализации ReferralMetrics."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = ReferralMetrics(
            overview=ReferralOverview(
                total_referrers=10,
                total_referred=50,
                referred_with_keys=40,
                referred_paying=20,
                conversion_to_keys=80.0,
                conversion_to_paid=40.0,
            ),
            top_referrers=[
                TopReferrer(
                    referrer_tg_id=123456,
                    referred_count=15,
                    paying_referrals=8,
                    total_revenue=5000.0,
                    conversion_rate=53.3,
                )
            ],
            total_revenue=10000.0,
            avg_revenue_per_referrer=1000.0,
        )

        data = ReferralMetricsService._metrics_to_dict(metrics)

        assert data["overview"]["total_referrers"] == 10
        assert len(data["top_referrers"]) == 1
        assert data["total_revenue"] == 10000.0

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "overview": {
                "total_referrers": 10,
                "total_referred": 50,
                "referred_with_keys": 40,
                "referred_paying": 20,
                "conversion_to_keys": 80.0,
                "conversion_to_paid": 40.0,
            },
            "top_referrers": [
                {
                    "referrer_tg_id": 123456,
                    "referred_count": 15,
                    "paying_referrals": 8,
                    "total_revenue": 5000.0,
                    "conversion_rate": 53.3,
                }
            ],
            "tariff_stats": [],
            "total_revenue": 10000.0,
            "avg_revenue_per_referrer": 1000.0,
        }

        metrics = ReferralMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, ReferralMetrics)
        assert metrics.overview.total_referrers == 10
        assert len(metrics.top_referrers) == 1

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = ReferralMetrics(
            overview=ReferralOverview(
                total_referrers=10,
                total_referred=50,
                referred_with_keys=40,
                referred_paying=20,
                conversion_to_keys=80.0,
                conversion_to_paid=40.0,
            ),
            total_revenue=10000.0,
            avg_revenue_per_referrer=1000.0,
        )

        data = ReferralMetricsService._metrics_to_dict(original)
        restored = ReferralMetricsService._dict_to_metrics(data)

        assert restored.overview.total_referrers == original.overview.total_referrers
        assert restored.total_revenue == original.total_revenue
