"""
Tests for CacheService.subscriptions namespace helpers.

These tests lock the contract that the subscription cache is accessed
via ``CacheService.subscriptions`` (not via ``cache.storage`` directly).
They are written *before* swapping the call sites so any regression
in the helpers is caught immediately.

Key contract: helpers must use the namespace ``"subscriptions"`` and
preserve the legacy key formats ``str(user_id)`` (status) and
``f"return_to:{user_id}"`` (return context) so the change is a pure
refactor with zero behavior change.
"""

import json
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from services.cache.service import CacheService
from services.cache.storage import CacheStorage


@pytest.fixture
def storage():
    return CacheStorage(cleanup_interval=timedelta(hours=1))


@pytest.fixture
def cache_service(storage):
    return CacheService(storage)


class TestSubscriptionsNamespace:
    def test_namespace_attribute_exists(self, cache_service):
        """CacheService must expose a ``subscriptions`` attribute on construction."""
        assert hasattr(cache_service, "subscriptions"), (
            "CacheService must expose a `subscriptions` namespace attribute"
        )

    def test_namespace_is_model_cache(self, cache_service):
        """subscriptions namespace must be a ModelCache[dict]."""
        from services.cache.service import ModelCache

        assert isinstance(cache_service.subscriptions, ModelCache)

    @pytest.mark.asyncio
    async def test_namespace_uses_subscriptions_label(self, storage, cache_service):
        """Underlying storage key prefix must be ``subscriptions``."""
        await cache_service.subscriptions.set("status_42", "1", ttl=timedelta(seconds=60))
        # Direct storage check
        assert "subscriptions" in storage._storage
        assert "status_42" in storage._storage["subscriptions"]


class TestSubscriptionStatus:
    @pytest.mark.asyncio
    async def test_get_status_cold_cache(self, cache_service):
        """Cold cache must return None."""
        result = await cache_service.get_subscription_status(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_status_round_trip(self, cache_service):
        """set + get must round-trip the boolean value."""
        await cache_service.set_subscription_status(
            user_id=123, is_subscribed=True, ttl=timedelta(seconds=60)
        )
        assert await cache_service.get_subscription_status(123) is True

    @pytest.mark.asyncio
    async def test_set_status_false_stores_zero(self, cache_service, storage):
        """set_subscription_status(False) must store ``"0"`` under str(user_id)."""
        await cache_service.set_subscription_status(
            user_id=42, is_subscribed=False, ttl=timedelta(seconds=60)
        )
        # Preserves legacy key format
        assert "42" in storage._storage["subscriptions"]
        assert storage._storage["subscriptions"]["42"].value == "0"

    @pytest.mark.asyncio
    async def test_set_status_true_stores_one(self, cache_service, storage):
        """set_subscription_status(True) must store ``"1"`` under str(user_id)."""
        await cache_service.set_subscription_status(
            user_id=42, is_subscribed=True, ttl=timedelta(seconds=60)
        )
        assert storage._storage["subscriptions"]["42"].value == "1"


class TestReturnContext:
    @pytest.mark.asyncio
    async def test_get_context_cold_cache(self, cache_service):
        """Cold cache must return None."""
        result = await cache_service.get_return_context(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_context_round_trip(self, cache_service):
        """set + get must round-trip the dict (JSON-encoded)."""
        context = {"callback_data": "renew_key|user@test.com", "event_type": "callback_query"}
        await cache_service.set_return_context(
            user_id=123, context=context, ttl=timedelta(seconds=300)
        )
        result = await cache_service.get_return_context(123)
        assert result == context

    @pytest.mark.asyncio
    async def test_set_context_uses_legacy_key(self, cache_service, storage):
        """Must use legacy key ``f"return_to:{user_id}"`` (with colon)."""
        await cache_service.set_return_context(
            user_id=99, context={"x": 1}, ttl=timedelta(seconds=300)
        )
        assert "return_to:99" in storage._storage["subscriptions"]

    @pytest.mark.asyncio
    async def test_get_context_handles_invalid_json(self, cache_service, storage):
        """Invalid JSON must return None, not raise."""
        await storage.set(
            namespace="subscriptions", key="return_to:77", value="not-json{", ttl=None
        )
        assert await cache_service.get_return_context(77) is None

    @pytest.mark.asyncio
    async def test_delete_return_context(self, cache_service):
        """delete_return_context must remove the entry."""
        await cache_service.set_return_context(
            user_id=55, context={"x": 1}, ttl=timedelta(seconds=60)
        )
        assert await cache_service.get_return_context(55) is not None
        await cache_service.delete_return_context(55)
        assert await cache_service.get_return_context(55) is None
