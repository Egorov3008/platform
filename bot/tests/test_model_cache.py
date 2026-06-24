import pytest
from unittest.mock import AsyncMock
from datetime import timedelta
from typing import TypeVar

from services.cache.service import ModelCache, CacheStorage, CacheService
from models import User

T = TypeVar("T")


class TestModelCache:
    """
    Тесты для ModelCache
    """

    @pytest.fixture
    def storage(self):
        return AsyncMock(spec=CacheStorage)

    @pytest.fixture
    def model_cache(self, storage):
        return ModelCache[User](storage, "test_namespace")

    async def test_set_calls_storage_set(self, model_cache, storage):
        """Проверяет, что set вызывает storage.set с правильными аргументами"""
        key = "user_123"
        value = User(tg_id=123, username="test")
        ttl = timedelta(hours=1)

        await model_cache.set(key, value, ttl)

        storage.set.assert_called_once_with("test_namespace", key, value, ttl)

    async def test_get_returns_value_from_storage(self, model_cache, storage):
        """Проверяет, что get возвращает значение из storage.get"""
        key = "user_123"
        expected_user = User(tg_id=123, username="test")
        storage.get.return_value = expected_user

        result = await model_cache.get(key)

        storage.get.assert_called_once_with("test_namespace", key)
        assert result == expected_user

    async def test_delete_calls_storage_delete(self, model_cache, storage):
        """Проверяет, что delete вызывает storage.delete"""
        key = "user_123"

        await model_cache.delete(key)

        storage.delete.assert_called_once_with("test_namespace", key)

    async def test_all_returns_all_values_from_storage(self, model_cache, storage):
        """Проверяет, что all возвращает все значения из storage.all_values"""
        expected_users = [
            User(tg_id=123, username="test1"),
            User(tg_id=456, username="test2"),
        ]
        storage.all_values.return_value = expected_users

        result = await model_cache.all()

        storage.all_values.assert_called_once_with("test_namespace")
        assert result == expected_users

    async def test_keys_returns_keys_from_storage(self, model_cache, storage):
        """Проверяет, что keys возвращает ключи из storage.keys"""
        expected_keys = ["user_123", "user_456"]
        storage.keys.return_value = expected_keys

        result = await model_cache.keys()

        storage.keys.assert_called_once_with("test_namespace")
        assert result == expected_keys

    async def test_temporary_set_calls_storage_set_with_prefix(
        self, model_cache, storage
    ):
        """Проверяет, что temporary_set вызывает storage.set с префиксом temporary_"""
        key = "temp_123"
        ttl = timedelta(minutes=30)
        data = {"some": "data"}

        await model_cache.temporary_set(key, ttl, **data)

        storage.set.assert_called_once_with(
            "test_namespace", f"temporary_{key}", data, ttl
        )

    async def test_temporary_get_calls_storage_get_with_prefix(
        self, model_cache, storage
    ):
        """Проверяет, что temporary_get вызывает storage.get с префиксом temporary_"""
        key = "temp_123"
        expected_data = {"some": "data"}
        storage.get.return_value = expected_data

        result = await model_cache.temporary_get(key)

        storage.get.assert_called_once_with("test_namespace", f"temporary_{key}")
        assert result == expected_data

    async def test_temporary_get_returns_none_when_no_data(self, model_cache, storage):
        """Проверяет, что temporary_get возвращает None, когда данных нет"""
        key = "nonexistent"
        storage.get.return_value = None

        result = await model_cache.temporary_get(key)

        assert result is None


class TestCacheService:
    """
    Тесты для CacheService
    """

    @pytest.fixture
    def storage(self):
        return AsyncMock(spec=CacheStorage)

    @pytest.fixture
    def cache_service(self, storage):
        return CacheService(storage)

    def test_cache_service_initialization_creates_all_caches(self, storage):
        """Проверяет, что при инициализации создаются все необходимые кеши"""
        cache_service = CacheService(storage)

        assert isinstance(cache_service.users, ModelCache)
        assert isinstance(cache_service.keys, ModelCache)
        assert isinstance(cache_service.servers, ModelCache)
        assert isinstance(cache_service.tariffs, ModelCache)
        assert isinstance(cache_service.gifts, ModelCache)
        assert isinstance(cache_service.payments, ModelCache)

        # Проверяем namespaces
        assert cache_service.users.namespace == "users"
        assert cache_service.keys.namespace == "keys"
        assert cache_service.servers.namespace == "servers"
        assert cache_service.tariffs.namespace == "tariffs"
        assert cache_service.gifts.namespace == "gift_links"
        assert cache_service.payments.namespace == "payments"

    def test_cache_service_stores_same_storage(self, storage):
        """Проверяет, что все кеши используют один и тот же storage"""
        cache_service = CacheService(storage)

        assert cache_service.users.storage == storage
        assert cache_service.keys.storage == storage
        assert cache_service.servers.storage == storage
        assert cache_service.tariffs.storage == storage
        assert cache_service.gifts.storage == storage
        assert cache_service.payments.storage == storage

    async def test_cache_service_start_calls_storage_start(
        self, cache_service, storage
    ):
        """Проверяет, что start вызывает storage.start"""
        await cache_service.start()
        storage.start.assert_called_once()

    async def test_cache_service_stop_calls_storage_stop(self, cache_service, storage):
        """Проверяет, что stop вызывает storage.stop"""
        await cache_service.stop()
        storage.stop.assert_called_once()
