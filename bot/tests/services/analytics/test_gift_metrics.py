"""Тесты для GiftMetricsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from services.analytics.gift_metrics import (
    GiftMetrics,
    GiftMetricsService,
    GiftOverview,
    GiftActivationStats,
    PopularGiftTariff,
)


class TestGiftMetricsDataclass:
    """Тесты для dataclass GiftMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = GiftMetrics()
        assert metrics.overview is None
        assert metrics.activation_stats is None
        assert metrics.popular_tariffs == []
        assert metrics.monthly_gifts == []

    def test_with_values(self):
        """Инициализация со значениями."""
        metrics = GiftMetrics(
            overview=GiftOverview(
                total_gifts=100,
                total_senders=50,
                total_recipients=80,
                activated_count=70,
                not_activated_count=30,
                activation_rate=70.0,
            ),
            activation_stats=GiftActivationStats(
                avg_activation_hours=24.5,
                median_activation_hours=12.0,
                activated_within_24h=40,
                activated_within_week=60,
            ),
        )
        assert metrics.overview.total_gifts == 100
        assert metrics.overview.activation_rate == 70.0
        assert metrics.activation_stats.avg_activation_hours == 24.5


class TestGiftMetricsService:
    """Тесты для GiftMetricsService."""

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
        return GiftMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_gift_metrics(self, service, mock_pool):
        """get_all_gift_metrics() возвращает GiftMetrics."""
        pool, mock_conn = mock_pool

        # Mock для overview
        overview_row = {
            "total_gifts": 100,
            "total_senders": 50,
            "total_recipients": 80,
            "activated_count": 70,
            "not_activated_count": 30,
        }

        # Mock для activation stats
        activation_row = {
            "avg_hours": 24.5,
            "median_hours": 12.0,
            "within_24h": 40,
            "within_week": 60,
            "total_activated": 70,
        }

        # Mock для популярных тарифов
        tariff_rows = [
            {
                "tariff_name": "Premium",
                "gifts_count": 50,
                "activated_count": 40,
                "activation_rate": 80.0,
            }
        ]

        # Mock для monthly gifts
        monthly_rows = [
            {
                "month": datetime(2026, 3, 1),
                "gifts_count": 30,
                "activated_count": 25,
                "activation_rate": 83.3,
            }
        ]

        mock_conn.fetchrow.side_effect = [overview_row, activation_row]
        mock_conn.fetch.side_effect = [tariff_rows, monthly_rows]

        metrics = await service.get_all_gift_metrics()

        assert isinstance(metrics, GiftMetrics)
        assert metrics.overview is not None
        assert metrics.overview.total_gifts == 100
        assert metrics.activation_stats is not None
        assert metrics.activation_stats.avg_activation_hours == 24.5
        assert len(metrics.popular_tariffs) == 1

    @pytest.mark.asyncio
    async def test_get_all_gift_metrics_empty_db(self, service, mock_pool):
        """get_all_gift_metrics() корректно обрабатывает пустую БД."""
        pool, mock_conn = mock_pool

        overview_row = {
            "total_gifts": 0,
            "total_senders": 0,
            "total_recipients": 0,
            "activated_count": 0,
            "not_activated_count": 0,
        }

        activation_row = {
            "avg_hours": 0,
            "median_hours": 0,
            "within_24h": 0,
            "within_week": 0,
            "total_activated": 0,
        }

        mock_conn.fetchrow.side_effect = [overview_row, activation_row]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_gift_metrics()

        assert isinstance(metrics, GiftMetrics)
        assert metrics.overview is not None
        assert metrics.overview.total_gifts == 0
        assert metrics.popular_tariffs == []

    @pytest.mark.asyncio
    async def test_activation_rate_calculation(self, service, mock_pool):
        """Процент активации рассчитывается корректно."""
        pool, mock_conn = mock_pool

        overview_row = {
            "total_gifts": 100,
            "total_senders": 50,
            "total_recipients": 80,
            "activated_count": 75,
            "not_activated_count": 25,
        }

        activation_row = {
            "avg_hours": 24.5,
            "median_hours": 12.0,
            "within_24h": 40,
            "within_week": 60,
            "total_activated": 75,
        }

        mock_conn.fetchrow.side_effect = [overview_row, activation_row]
        mock_conn.fetch.return_value = []

        metrics = await service.get_all_gift_metrics()

        assert metrics.overview.activation_rate == 75.0
        assert metrics.overview.activated_count == 75
        assert metrics.overview.not_activated_count == 25


class TestGiftMetricsServiceCaching:
    """Тесты для кэширования Gift-метрик."""

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
        service = GiftMetricsService(pool)

        cached_data = {
            "overview": {
                "total_gifts": 100,
                "total_senders": 50,
                "total_recipients": 80,
                "activated_count": 70,
                "not_activated_count": 30,
                "activation_rate": 70.0,
            },
            "activation_stats": {
                "avg_activation_hours": 24.5,
                "median_activation_hours": 12.0,
                "activated_within_24h": 40,
                "activated_within_week": 60,
            },
            "popular_tariffs": [],
            "monthly_gifts": [],
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, GiftMetrics)
        assert metrics.overview.total_gifts == 100
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = GiftMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        overview_row = {
            "total_gifts": 0,
            "total_senders": 0,
            "total_recipients": 0,
            "activated_count": 0,
            "not_activated_count": 0,
        }

        activation_row = {
            "avg_hours": 0,
            "median_hours": 0,
            "within_24h": 0,
            "within_week": 0,
            "total_activated": 0,
        }

        mock_conn.fetchrow.side_effect = [overview_row, activation_row]
        mock_conn.fetch.return_value = []

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert isinstance(metrics, GiftMetrics)
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"
        assert call_args[1] == "gift_metrics"


class TestMetricsSerialization:
    """Тесты сериализации/десериализации GiftMetrics."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = GiftMetrics(
            overview=GiftOverview(
                total_gifts=100,
                total_senders=50,
                total_recipients=80,
                activated_count=70,
                not_activated_count=30,
                activation_rate=70.0,
            ),
            activation_stats=GiftActivationStats(
                avg_activation_hours=24.5,
                median_activation_hours=12.0,
                activated_within_24h=40,
                activated_within_week=60,
            ),
            popular_tariffs=[
                PopularGiftTariff(
                    tariff_name="Premium",
                    gifts_count=50,
                    activated_count=40,
                    activation_rate=80.0,
                )
            ],
        )

        data = GiftMetricsService._metrics_to_dict(metrics)

        assert data["overview"]["total_gifts"] == 100
        assert data["activation_stats"]["avg_activation_hours"] == 24.5
        assert len(data["popular_tariffs"]) == 1

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "overview": {
                "total_gifts": 100,
                "total_senders": 50,
                "total_recipients": 80,
                "activated_count": 70,
                "not_activated_count": 30,
                "activation_rate": 70.0,
            },
            "activation_stats": {
                "avg_activation_hours": 24.5,
                "median_activation_hours": 12.0,
                "activated_within_24h": 40,
                "activated_within_week": 60,
            },
            "popular_tariffs": [
                {
                    "tariff_name": "Premium",
                    "gifts_count": 50,
                    "activated_count": 40,
                    "activation_rate": 80.0,
                }
            ],
            "monthly_gifts": [],
        }

        metrics = GiftMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, GiftMetrics)
        assert metrics.overview.total_gifts == 100
        assert len(metrics.popular_tariffs) == 1

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = GiftMetrics(
            overview=GiftOverview(
                total_gifts=100,
                total_senders=50,
                total_recipients=80,
                activated_count=70,
                not_activated_count=30,
                activation_rate=70.0,
            ),
            activation_stats=GiftActivationStats(
                avg_activation_hours=24.5,
                median_activation_hours=12.0,
                activated_within_24h=40,
                activated_within_week=60,
            ),
        )

        data = GiftMetricsService._metrics_to_dict(original)
        restored = GiftMetricsService._dict_to_metrics(data)

        assert restored.overview.total_gifts == original.overview.total_gifts
        assert restored.activation_stats.avg_activation_hours == original.activation_stats.avg_activation_hours
