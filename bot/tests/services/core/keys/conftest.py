"""
Фикстуры для интеграционных тестов KeyResetter.

Использует моки для БД и кэша для изолированного тестирования.
Для полноценных интеграционных тестов с PostgreSQL/Redis использовать
testcontainers или docker-compose с тестовыми контейнерами.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from models import Key
from services.cache.service import CacheService
from services.core.keys.utils.reset import KeyResetter


@pytest.fixture
def test_key():
    """Создаёт тестовый ключ с установленными флагами уведомлений."""
    return Key(
        email="test_reset@example.com",
        inbound_id=12,
        client_id="client_reset_test",
        tg_id=123456789,
        key="test_key_data_reset",
        expiry_time=int(datetime.now().timestamp() * 1000) + 86400000,  # +1 день
        tariff_id=1,
        notified_24h=True,
        notified_10h=True,
        used_traffic=50.5,  # Установим ненулевое значение
        total_gb=100 * (2**30),
    )


@pytest.fixture
def mock_cache_service():
    """Создаёт мок CacheService для тестирования."""
    cache = MagicMock(spec=CacheService)
    cache.keys = AsyncMock()
    cache.keys.set = AsyncMock()
    cache.keys.get = AsyncMock()
    cache.keys.delete = AsyncMock()
    return cache


@pytest.fixture
def mock_db_pool():
    """Создаёт мок asyncpg.Pool для тестирования."""
    pool = AsyncMock(spec=asyncpg.Pool)
    pool.execute = AsyncMock(return_value="UPDATE 1")
    return pool


@pytest.fixture
def resetter(mock_cache_service):
    """Создаёт экземпляр KeyResetter с мокнутым CacheService."""
    return KeyResetter(cache_service=mock_cache_service)


@pytest.fixture
def integration_test_setup():
    """
    Фикстура для настройки интеграционных тестов.
    
    Для реальных интеграционных тестов с PostgreSQL и Redis:
    1. Использовать testcontainers-python для запуска контейнеров
    2. Или использовать docker-compose с тестовым профилем
    
    Пример с testcontainers:
    ```python
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    
    @pytest.fixture
    def db_container():
        with PostgresContainer("postgres:15") as postgres:
            yield postgres.get_connection_url()
    
    @pytest.fixture
    def redis_container():
        with RedisContainer("redis:7") as redis:
            yield redis.get_connection_url()
    ```
    """
    return {
        "db_url": "postgresql://test:test@localhost:5432/test_bot",
        "redis_url": "redis://localhost:6379/0",
    }
