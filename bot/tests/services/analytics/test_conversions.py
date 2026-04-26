"""Тесты для ConversionMetricsService.

Тесты проверяют корректность расчёта метрик конверсий через SQL-агрегаты.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from services.analytics.conversions import (
    ConversionMetrics,
    ConversionMetricsService,
    TariffStat,
    _pct,
)


class TestHelperFunctions:
    """Тесты для вспомогательных функций."""

    def test_pct_normal(self):
        """Процент от нормальных чисел."""
        assert _pct(25, 100) == 25.0
        assert _pct(50, 200) == 25.0
        assert _pct(3, 7) == 42.9

    def test_pct_zero_denominator(self):
        """Защита от деления на ноль."""
        assert _pct(0, 0) == 0.0
        assert _pct(5, 0) == 0.0

    def test_pct_rounding(self):
        """Округление до 1 знака."""
        assert _pct(1, 3) == 33.3
        assert _pct(2, 3) == 66.7


class TestConversionMetricsDataclass:
    """Тесты для dataclass ConversionMetrics."""

    def test_default_values(self):
        """Значения по умолчанию."""
        metrics = ConversionMetrics()
        assert metrics.year == 0
        assert metrics.total_users == 0
        assert metrics.tariff_stats == []
        assert metrics.total_revenue_this_year == 0.0

    def test_with_values(self):
        """Инициализация со значениями."""
        stats = [TariffStat("Premium", 10, 5000.0)]
        metrics = ConversionMetrics(
            year=2026,
            total_users=100,
            tariff_stats=stats,
            total_revenue_this_year=5000.0,
        )
        assert metrics.year == 2026
        assert metrics.total_users == 100
        assert len(metrics.tariff_stats) == 1


class TestConversionMetricsService:
    """Тесты для ConversionMetricsService."""

    @pytest.fixture
    def mock_pool(self):
        """Создаёт mock пул соединений с правильным async context manager."""
        from unittest.mock import MagicMock
        
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool, mock_conn

    @pytest.fixture
    def service(self, mock_pool):
        """Создаёт сервис с mock пулом."""
        pool, _ = mock_pool
        return ConversionMetricsService(pool)

    @pytest.mark.asyncio
    async def test_get_all_returns_metrics(self, service, mock_pool):
        """get_all() возвращает ConversionMetrics с данными."""
        pool, mock_conn = mock_pool
        
        # Настраиваем mock для основного запроса
        mock_record = {
            "total_users": 100,
            "users_with_keys": 80,
            "users_with_active_keys": 60,
            "trial_keys_active": 20,
            "paid_keys_active": 40,
            "reg_year": 50,
            "reg_month": 10,
            "reg_week": 3,
            "trial_activated": 30,
            "trial_to_paid": 15,
            "payers_this_year": 25,
            "repeat_payers": 10,
            "referred_this_year": 20,
            "referred_paid_this_year": 8,
            "gifts_this_year": 5,
            "gifts_activated_this_year": 3,
        }

        # Настраиваем mock для запроса тарифов
        mock_tariff_rows = [
            {"tariff_name": "Premium", "keys_count": 10, "total_amount": 5000.0},
            {"tariff_name": "Basic", "keys_count": 15, "total_amount": 3000.0},
        ]

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = mock_tariff_rows

        metrics = await service.get_all()

        assert isinstance(metrics, ConversionMetrics)
        assert metrics.year == datetime.now(timezone.utc).year
        assert metrics.total_users == 100
        assert metrics.users_with_keys == 80
        assert metrics.registered_this_year == 50
        assert metrics.trial_activated_this_year == 30
        assert metrics.trial_to_paid_this_year == 15

    @pytest.mark.asyncio
    async def test_get_all_calculates_percentages(self, service, mock_pool):
        """get_all() корректно вычисляет проценты."""
        pool, mock_conn = mock_pool
        
        mock_record = {
            "total_users": 100,
            "users_with_keys": 80,
            "users_with_active_keys": 60,
            "trial_keys_active": 20,
            "paid_keys_active": 40,
            "reg_year": 100,
            "reg_month": 10,
            "reg_week": 3,
            "trial_activated": 50,
            "trial_to_paid": 25,
            "payers_this_year": 40,
            "repeat_payers": 20,
            "referred_this_year": 30,
            "referred_paid_this_year": 15,
            "gifts_this_year": 10,
            "gifts_activated_this_year": 5,
        }

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = []

        metrics = await service.get_all()

        assert metrics.reg_to_trial_pct == 50.0  # 50/100
        assert metrics.trial_to_paid_pct == 50.0  # 25/50
        assert metrics.retention_pct == 50.0  # 20/40
        assert metrics.referral_pct == 50.0  # 15/30
        assert metrics.gift_pct == 50.0  # 5/10

    @pytest.mark.asyncio
    async def test_get_all_handles_zero_values(self, service, mock_pool):
        """get_all() корректно обрабатывает нулевые значения."""
        pool, mock_conn = mock_pool
        
        mock_record = {
            "total_users": 0,
            "users_with_keys": 0,
            "users_with_active_keys": 0,
            "trial_keys_active": 0,
            "paid_keys_active": 0,
            "reg_year": 0,
            "reg_month": 0,
            "reg_week": 0,
            "trial_activated": 0,
            "trial_to_paid": 0,
            "payers_this_year": 0,
            "repeat_payers": 0,
            "referred_this_year": 0,
            "referred_paid_this_year": 0,
            "gifts_this_year": 0,
            "gifts_activated_this_year": 0,
        }

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = []

        metrics = await service.get_all()

        assert metrics.total_users == 0
        assert metrics.reg_to_trial_pct == 0.0
        assert metrics.trial_to_paid_pct == 0.0
        assert metrics.overall_conversion_pct == 0.0

    @pytest.mark.asyncio
    async def test_get_all_fetches_tariff_stats(self, service, mock_pool):
        """get_all() загружает статистику по тарифам."""
        pool, mock_conn = mock_pool
        
        mock_record = {
            "total_users": 100,
            "users_with_keys": 80,
            "users_with_active_keys": 60,
            "trial_keys_active": 20,
            "paid_keys_active": 40,
            "reg_year": 50,
            "reg_month": 10,
            "reg_week": 3,
            "trial_activated": 30,
            "trial_to_paid": 15,
            "payers_this_year": 25,
            "repeat_payers": 10,
            "referred_this_year": 20,
            "referred_paid_this_year": 8,
            "gifts_this_year": 5,
            "gifts_activated_this_year": 3,
        }

        mock_tariff_rows = [
            {"tariff_name": "Premium", "keys_count": 10, "total_amount": 5000.0},
            {"tariff_name": "Basic", "keys_count": 15, "total_amount": 3000.0},
        ]

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = mock_tariff_rows

        metrics = await service.get_all()

        assert len(metrics.tariff_stats) == 2
        assert metrics.tariff_stats[0].tariff_name == "Premium"
        assert metrics.tariff_stats[0].payment_count == 10
        assert metrics.tariff_stats[0].total_amount == 5000.0
        assert metrics.total_revenue_this_year == 8000.0

    @pytest.mark.asyncio
    async def test_get_all_calls_db_with_correct_params(self, service, mock_pool):
        """get_all() вызывает БД с правильными параметрами дат."""
        pool, mock_conn = mock_pool
        
        mock_record = {
            "total_users": 0, "users_with_keys": 0, "users_with_active_keys": 0,
            "trial_keys_active": 0, "paid_keys_active": 0,
            "reg_year": 0, "reg_month": 0, "reg_week": 0,
            "trial_activated": 0, "trial_to_paid": 0,
            "payers_this_year": 0, "repeat_payers": 0,
            "referred_this_year": 0, "referred_paid_this_year": 0,
            "gifts_this_year": 0, "gifts_activated_this_year": 0,
        }

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = []

        await service.get_all()

        # Проверяем, что fetchrow был вызван
        assert mock_conn.fetchrow.called
        call_args = mock_conn.fetchrow.call_args[0]
        # Первый аргумент - SQL запрос
        assert isinstance(call_args[0], str)
        assert "WITH" in call_args[0].upper()  # CTE запрос


class TestConversionMetricsServiceCaching:
    """Тесты для кэширования метрик."""

    @pytest.fixture
    def mock_pool(self):
        from unittest.mock import MagicMock
        
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
        service = ConversionMetricsService(pool)

        cached_data = {
            "year": 2026,
            "total_users": 100,
            "users_with_keys": 80,
            "users_with_active_keys": 60,
            "trial_keys_active": 20,
            "paid_keys_active": 40,
            "registered_this_year": 50,
            "registered_this_month": 10,
            "registered_this_week": 3,
            "trial_activated_this_year": 30,
            "reg_to_trial_pct": 60.0,
            "trial_to_paid_this_year": 15,
            "trial_to_paid_pct": 50.0,
            "payers_this_year": 25,
            "repeat_payers_this_year": 10,
            "retention_pct": 40.0,
            "overall_conversion_pct": 30.0,
            "referred_this_year": 20,
            "referred_paid_this_year": 8,
            "referral_pct": 40.0,
            "gifts_this_year": 5,
            "gifts_activated_this_year": 3,
            "gift_pct": 60.0,
            "tariff_stats": [
                {"tariff_name": "Premium", "payment_count": 10, "total_amount": 5000.0}
            ],
            "total_revenue_this_year": 5000.0,
        }

        mock_cache_service.storage.get.return_value = cached_data

        metrics = await service.get_cached(mock_cache_service)

        assert isinstance(metrics, ConversionMetrics)
        assert metrics.total_users == 100
        mock_cache_service.storage.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_computes_and_caches(self, mock_pool, mock_cache_service):
        """get_cached() вычисляет и кэширует если нет в кэше."""
        pool, mock_conn = mock_pool
        service = ConversionMetricsService(pool)

        mock_cache_service.storage.get.return_value = None

        mock_record = {
            "total_users": 150,
            "users_with_keys": 100,
            "users_with_active_keys": 80,
            "trial_keys_active": 30,
            "paid_keys_active": 50,
            "reg_year": 75,
            "reg_month": 15,
            "reg_week": 5,
            "trial_activated": 45,
            "trial_to_paid": 20,
            "payers_this_year": 35,
            "repeat_payers": 15,
            "referred_this_year": 25,
            "referred_paid_this_year": 10,
            "gifts_this_year": 8,
            "gifts_activated_this_year": 4,
        }

        mock_tariff_rows = [
            {"tariff_name": "Premium", "keys_count": 12, "total_amount": 6000.0}
        ]

        mock_conn.fetchrow.return_value = mock_record
        mock_conn.fetch.return_value = mock_tariff_rows

        metrics = await service.get_cached(mock_cache_service, ttl_seconds=600)

        assert metrics.total_users == 150
        mock_cache_service.storage.set.assert_called_once()
        call_args = mock_cache_service.storage.set.call_args[0]
        assert call_args[0] == "analytics"  # namespace
        assert call_args[1] == "conversion_metrics"  # key


class TestMetricsSerialization:
    """Тесты сериализации/десериализации метрик."""

    def test_metrics_to_dict(self):
        """Сериализация метрик в dict."""
        metrics = ConversionMetrics(
            year=2026,
            total_users=100,
            users_with_keys=80,
            users_with_active_keys=60,
            trial_keys_active=20,
            paid_keys_active=40,
            registered_this_year=50,
            registered_this_month=10,
            registered_this_week=3,
            trial_activated_this_year=30,
            reg_to_trial_pct=60.0,
            trial_to_paid_this_year=15,
            trial_to_paid_pct=50.0,
            payers_this_year=25,
            repeat_payers_this_year=10,
            retention_pct=40.0,
            overall_conversion_pct=30.0,
            referred_this_year=20,
            referred_paid_this_year=8,
            referral_pct=40.0,
            gifts_this_year=5,
            gifts_activated_this_year=3,
            gift_pct=60.0,
            tariff_stats=[
                TariffStat("Premium", 10, 5000.0),
                TariffStat("Basic", 15, 3000.0),
            ],
            total_revenue_this_year=8000.0,
        )

        data = ConversionMetricsService._metrics_to_dict(metrics)

        assert data["year"] == 2026
        assert data["total_users"] == 100
        assert len(data["tariff_stats"]) == 2
        assert data["total_revenue_this_year"] == 8000.0

    def test_dict_to_metrics(self):
        """Десериализация dict в метрики."""
        data = {
            "year": 2026,
            "total_users": 100,
            "users_with_keys": 80,
            "users_with_active_keys": 60,
            "trial_keys_active": 20,
            "paid_keys_active": 40,
            "registered_this_year": 50,
            "registered_this_month": 10,
            "registered_this_week": 3,
            "trial_activated_this_year": 30,
            "reg_to_trial_pct": 60.0,
            "trial_to_paid_this_year": 15,
            "trial_to_paid_pct": 50.0,
            "payers_this_year": 25,
            "repeat_payers_this_year": 10,
            "retention_pct": 40.0,
            "overall_conversion_pct": 30.0,
            "referred_this_year": 20,
            "referred_paid_this_year": 8,
            "referral_pct": 40.0,
            "gifts_this_year": 5,
            "gifts_activated_this_year": 3,
            "gift_pct": 60.0,
            "tariff_stats": [
                {"tariff_name": "Premium", "payment_count": 10, "total_amount": 5000.0},
                {"tariff_name": "Basic", "payment_count": 15, "total_amount": 3000.0},
            ],
            "total_revenue_this_year": 8000.0,
        }

        metrics = ConversionMetricsService._dict_to_metrics(data)

        assert isinstance(metrics, ConversionMetrics)
        assert metrics.year == 2026
        assert metrics.total_users == 100
        assert len(metrics.tariff_stats) == 2
        assert metrics.tariff_stats[0].tariff_name == "Premium"

    def test_roundtrip_serialization(self):
        """Круговое преобразование metrics → dict → metrics."""
        original = ConversionMetrics(
            year=2026,
            total_users=100,
            tariff_stats=[TariffStat("Premium", 10, 5000.0)],
            total_revenue_this_year=5000.0,
        )

        data = ConversionMetricsService._metrics_to_dict(original)
        restored = ConversionMetricsService._dict_to_metrics(data)

        assert restored.year == original.year
        assert restored.total_users == original.total_users
        assert len(restored.tariff_stats) == len(original.tariff_stats)
        assert restored.total_revenue_this_year == original.total_revenue_this_year
