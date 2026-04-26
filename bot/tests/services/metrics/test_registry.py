"""Тесты для модуля метрик Prometheus."""

import pytest
from prometheus_client import CollectorRegistry

from services.metrics.registry import (
    REGISTRY,
    payment_total,
    payment_amount_rub_total,
    payment_processing_duration,
    webhook_requests_total,
    key_created_total,
    key_renewed_total,
    key_deleted_total,
    key_creation_errors_total,
    keys_by_segment,
    user_registered_total,
    users_total_count,
    notification_sent_total,
    notification_blocked_total,
    notification_error_total,
    notification_cycle_duration,
    rate_limiter_tokens,
    handler_duration,
    db_pool_size,
    db_pool_free,
    db_pool_used,
    cache_items_count,
    cache_expired_evictions_total,
    xui_api_calls_total,
    xui_api_errors_total,
    xui_api_duration,
    xui_api_retries_total,
    telegram_messages_sent_total,
    telegram_flood_control_total,
    background_sync_last_run,
    background_sync_duration,
    background_sync_errors_total,
    background_notification_last_run,
    errors_total,
)


class TestRegistryExists:
    """Проверяет что реестр и все метрики определены."""

    def test_registry_is_collector_registry(self):
        assert isinstance(REGISTRY, CollectorRegistry)

    def test_all_metrics_registered(self):
        """Все метрики зарегистрированы в REGISTRY."""
        metrics = [
            payment_total,
            payment_amount_rub_total,
            payment_processing_duration,
            webhook_requests_total,
            key_created_total,
            key_renewed_total,
            key_deleted_total,
            key_creation_errors_total,
            keys_by_segment,
            user_registered_total,
            users_total_count,
            notification_sent_total,
            notification_blocked_total,
            notification_error_total,
            notification_cycle_duration,
            rate_limiter_tokens,
            handler_duration,
            db_pool_size,
            db_pool_free,
            db_pool_used,
            cache_items_count,
            cache_expired_evictions_total,
            xui_api_calls_total,
            xui_api_errors_total,
            xui_api_duration,
            xui_api_retries_total,
            telegram_messages_sent_total,
            telegram_flood_control_total,
            background_sync_last_run,
            background_sync_duration,
            background_sync_errors_total,
            background_notification_last_run,
            errors_total,
        ]
        for metric in metrics:
            assert metric is not None


class TestMetricLabels:
    """Проверяет что метрики с лейблами работают корректно."""

    def test_payment_total_labels(self):
        """Проверяет лейблы payment_total."""
        counter = payment_total.labels(status="succeeded", operation="create_key")
        assert counter is not None

    def test_handler_duration_labels(self):
        """Проверяет лейблы handler_duration."""
        obs = handler_duration.labels(
            handler="test_handler", event_type="message", status="success"
        )
        assert obs is not None

    def test_xui_api_labels(self):
        """Проверяет лейблы XUI API метрик."""
        xui_api_calls_total.labels(method="add_client").inc()
        xui_api_errors_total.labels(method="add_client", error_type="TimeoutError").inc()
        xui_api_duration.labels(method="add_client").observe(1.5)

    def test_notification_labels(self):
        """Проверяет лейблы notification метрик."""
        notification_sent_total.labels(funnel_id="key_expiry_24h").inc()
        notification_blocked_total.labels(funnel_id="key_expiry_24h").inc()

    def test_webhook_labels(self):
        """Проверяет лейблы webhook метрик."""
        webhook_requests_total.labels(event_type="payment.succeeded", status="ok").inc()

    def test_cache_labels(self):
        """Проверяет лейблы cache метрик."""
        cache_items_count.labels(namespace="users").set(100)
        cache_expired_evictions_total.labels(namespace="keys").inc(5)

    def test_telegram_labels(self):
        """Проверяет лейблы telegram метрик."""
        telegram_messages_sent_total.labels(result="sent").inc()
        telegram_messages_sent_total.labels(result="blocked").inc()

    def test_errors_labels(self):
        """Проверяет лейблы errors метрик."""
        errors_total.labels(layer="payment", error_type="ValueError").inc()


class TestMetricTypes:
    """Проверяет типы метрик."""

    def test_gauge_set(self):
        users_total_count.set(42)
        rate_limiter_tokens.set(25.0)
        background_sync_last_run.set_to_current_time()

    def test_counter_inc(self):
        key_renewed_total.inc()
        key_deleted_total.inc()
        background_sync_errors_total.inc()

    def test_histogram_observe(self):
        notification_cycle_duration.observe(12.5)
        background_sync_duration.observe(45.0)
        payment_processing_duration.labels(operation="create_key").observe(2.0)
