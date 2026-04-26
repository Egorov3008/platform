"""Тесты для кастомных Collector'ов."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta

from services.metrics.collectors.cache_collector import CacheMetricsCollector
from services.metrics.collectors.db_pool_collector import DBPoolMetricsCollector


class TestCacheMetricsCollector:
    """Тесты для CacheMetricsCollector."""

    def test_collect_empty_storage(self):
        storage = MagicMock()
        storage._storage = {}
        collector = CacheMetricsCollector(storage)

        metrics = list(collector.collect())
        assert len(metrics) == 1
        assert metrics[0].name == "vpn_cache_items_count"
        assert len(metrics[0].samples) == 0

    def test_collect_with_namespaces(self):
        storage = MagicMock()
        storage._storage = {
            "users": {"u1": MagicMock(), "u2": MagicMock()},
            "keys": {"k1": MagicMock()},
            "servers": {},
        }
        collector = CacheMetricsCollector(storage)

        metrics = list(collector.collect())
        assert len(metrics) == 1
        samples = metrics[0].samples

        # Проверяем значения по namespace
        values_by_ns = {s.labels["namespace"]: s.value for s in samples}
        assert values_by_ns["users"] == 2
        assert values_by_ns["keys"] == 1
        assert values_by_ns["servers"] == 0

    def test_describe_returns_empty(self):
        storage = MagicMock()
        storage._storage = {}
        collector = CacheMetricsCollector(storage)
        assert collector.describe() == []


class TestDBPoolMetricsCollector:
    """Тесты для DBPoolMetricsCollector."""

    def test_collect_pool_stats(self):
        pool = MagicMock()
        pool.get_size.return_value = 10
        pool.get_idle_size.return_value = 7

        collector = DBPoolMetricsCollector(pool)
        metrics = list(collector.collect())

        assert len(metrics) == 3
        names = [m.name for m in metrics]
        assert "vpn_db_pool_size" in names
        assert "vpn_db_pool_free" in names
        assert "vpn_db_pool_used" in names

        values = {m.name: m.samples[0].value for m in metrics}
        assert values["vpn_db_pool_size"] == 10
        assert values["vpn_db_pool_free"] == 7
        assert values["vpn_db_pool_used"] == 3

    def test_collect_fully_utilized_pool(self):
        pool = MagicMock()
        pool.get_size.return_value = 5
        pool.get_idle_size.return_value = 0

        collector = DBPoolMetricsCollector(pool)
        metrics = list(collector.collect())

        values = {m.name: m.samples[0].value for m in metrics}
        assert values["vpn_db_pool_used"] == 5

    def test_describe_returns_empty(self):
        pool = MagicMock()
        collector = DBPoolMetricsCollector(pool)
        assert collector.describe() == []
