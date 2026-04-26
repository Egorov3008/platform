"""
Интеграционные тесты для KeyResetter.

Тестируют:
1. Сброс флагов notified_24h, notified_10h в БД
2. Сброс used_traffic в 0.0
3. Обновление кеша после сброса
4. Полный цикл продления ключа

Для полноценных интеграционных тестов требуется:
- PostgreSQL (реальный или testcontainers)
- Redis (реальный или testcontainers)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call

import asyncpg
import pytest

from models import Key
from services.core.keys.utils.reset import KeyResetter


class TestResetterBasic:
    """Базовые тесты сброса флагов KeyResetter."""

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_resets_flags(
        self, resetter: KeyResetter, mock_db_pool, test_key
    ):
        """
        Тест сброса флагов уведомлений в БД.
        
        Проверяет:
        - notified_24h = FALSE
        - notified_10h = FALSE
        - used_traffic = 0.0
        """
        # Arrange: ключ имеет установленные флаги
        assert test_key.notified_24h is True
        assert test_key.notified_10h is True
        assert test_key.used_traffic == 50.5

        # Act: выполняем сброс
        result = await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert: флаги сброшены
        assert result is True
        assert test_key.notified_24h is False
        assert test_key.notified_10h is False
        assert test_key.used_traffic == 0.0

        # Проверяем что SQL UPDATE был вызван
        mock_db_pool.execute.assert_called_once()
        sql_query = mock_db_pool.execute.call_args[0][0]
        assert "UPDATE keys" in sql_query
        assert "notified_24h = FALSE" in sql_query
        assert "notified_10h = FALSE" in sql_query
        assert "used_traffic = 0.0" in sql_query

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_returns_false_when_key_not_found(
        self, resetter: KeyResetter, mock_db_pool, test_key
    ):
        """Тест обработки случая когда ключ не найден в БД."""
        # Arrange: UPDATE не затронул ни одной строки
        mock_db_pool.execute = AsyncMock(return_value="UPDATE 0")

        # Act
        result = await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert: возвращаем False
        assert result is False
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_updates_local_key_object(
        self, resetter: KeyResetter, mock_db_pool, test_key
    ):
        """Тест обновления локального объекта ключа."""
        # Arrange
        original_notified_24h = test_key.notified_24h
        original_notified_10h = test_key.notified_10h
        original_used_traffic = test_key.used_traffic

        # Act
        await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert: объект изменён
        assert test_key.notified_24h is False
        assert test_key.notified_10h is False
        assert test_key.used_traffic == 0.0
        # Проверяем что значения изменились
        assert test_key.notified_24h != original_notified_24h
        assert test_key.notified_10h != original_notified_10h
        assert test_key.used_traffic != original_used_traffic


class TestResetterCache:
    """Тесты обновления кеша KeyResetter."""

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_updates_cache(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """
        Тест обновления кеша после сброса флагов.
        
        Проверяет что cache_service.keys.set() был вызван
        с правильным ключом и обновлённым объектом ключа.
        """
        # Act
        await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert: кеш был обновлён
        mock_cache_service.keys.set.assert_called_once()
        call_args = mock_cache_service.keys.set.call_args

        # Проверяем ключ кеша
        cache_key = call_args[0][0]
        assert cache_key == "key_test_reset@example.com"

        # Проверяем что объект в кеше имеет сброшенные флаги
        cached_key = call_args[0][1]
        assert cached_key.notified_24h is False
        assert cached_key.notified_10h is False
        assert cached_key.used_traffic == 0.0

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_cache_key_format(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """Тест формата ключа кеша."""
        # Act
        await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert
        mock_cache_service.keys.set.assert_called_once()
        cache_key = mock_cache_service.keys.set.call_args[0][0]
        # Ключ должен быть в формате key_{email}
        assert cache_key.startswith("key_")
        assert test_key.email in cache_key

    @pytest.mark.asyncio
    async def test_reset_key_after_renewal_cache_not_called_on_db_error(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """Тест что кеш не обновляется при ошибке БД."""
        # Arrange: ошибка БД
        mock_db_pool.execute = AsyncMock(side_effect=Exception("DB connection error"))

        # Act & Assert: ошибка пробрасывается вверх
        with pytest.raises(Exception, match="DB connection error"):
            await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Кеш не должен быть обновлён
        mock_cache_service.keys.set.assert_not_called()


class TestResetterIntegration:
    """
    Интеграционные тесты полного цикла продления.
    
    Для реальных тестов с PostgreSQL/Redis использовать:
    - testcontainers-python
    - Или docker-compose с тестовым профилем
    """

    @pytest.mark.asyncio
    async def test_full_renewal_cycle(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """
        Тест полного цикла сброса ключа после продления.
        
        Сценарий:
        1. Ключ имеет флаги notified_24h=True, notified_10h=True
        2. Ключ имеет used_traffic=50.5
        3. Вызываем reset_key_after_renewal()
        4. Проверяем БД UPDATE
        5. Проверяем обновление кеша
        6. Проверяем локальный объект
        """
        # Arrange: начальное состояние
        initial_state = {
            "notified_24h": test_key.notified_24h,
            "notified_10h": test_key.notified_10h,
            "used_traffic": test_key.used_traffic,
        }
        assert initial_state["notified_24h"] is True
        assert initial_state["notified_10h"] is True
        assert initial_state["used_traffic"] > 0

        # Act: сброс после продления
        result = await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # Assert: все изменения применены
        assert result is True

        # 1. БД обновлена
        mock_db_pool.execute.assert_called_once()

        # 2. Кеш обновлён
        mock_cache_service.keys.set.assert_called_once()

        # 3. Локальный объект обновлён
        assert test_key.notified_24h is False
        assert test_key.notified_10h is False
        assert test_key.used_traffic == 0.0

        # 4. Данные в кеше корректны
        cached_key = mock_cache_service.keys.set.call_args[0][1]
        assert cached_key.notified_24h is False
        assert cached_key.notified_10h is False
        assert cached_key.used_traffic == 0.0

    @pytest.mark.asyncio
    async def test_multiple_resets_sequential(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """Тест множественных последовательных сбросов."""
        # Arrange
        mock_db_pool.execute = AsyncMock(return_value="UPDATE 1")

        # Act: первый сброс
        await resetter.reset_key_after_renewal(mock_db_pool, test_key)
        first_cache_call_args = mock_cache_service.keys.set.call_args

        # Сбрасываем моки для второго вызова
        mock_db_pool.execute.reset_mock()
        mock_cache_service.keys.set.reset_mock()

        # Act: второй сброс
        await resetter.reset_key_after_renewal(mock_db_pool, test_key)
        second_cache_call_args = mock_cache_service.keys.set.call_args

        # Assert: оба вызова успешны
        assert mock_db_pool.execute.call_count == 1
        assert mock_cache_service.keys.set.call_count == 1

        # Кеш обновляется каждый раз
        assert second_cache_call_args[0][1].notified_24h is False
        assert second_cache_call_args[0][1].used_traffic == 0.0


class TestResetterEdgeCases:
    """Тесты граничных случаев и ошибок."""

    @pytest.mark.asyncio
    async def test_reset_key_with_zero_used_traffic(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service
    ):
        """Тест сброса ключа с уже нулевым трафиком."""
        # Arrange
        key = Key(
            email="zero_traffic@example.com",
            inbound_id=12,
            client_id="client_zero",
            tg_id=123456789,
            key="test_key",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
            notified_24h=True,
            notified_10h=True,
            used_traffic=0.0,  # Уже ноль
        )

        # Act
        result = await resetter.reset_key_after_renewal(mock_db_pool, key)

        # Assert
        assert result is True
        assert key.used_traffic == 0.0
        mock_cache_service.keys.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_key_with_flags_already_false(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service
    ):
        """Тест сброса ключа с уже сброшенными флагами."""
        # Arrange
        key = Key(
            email="already_reset@example.com",
            inbound_id=12,
            client_id="client_reset",
            tg_id=123456789,
            key="test_key",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
            notified_24h=False,  # Уже сброшен
            notified_10h=False,  # Уже сброшен
            used_traffic=25.0,
        )

        # Act
        result = await resetter.reset_key_after_renewal(mock_db_pool, key)

        # Assert
        assert result is True
        assert key.notified_24h is False
        assert key.notified_10h is False
        assert key.used_traffic == 0.0

    @pytest.mark.asyncio
    async def test_reset_key_database_error_handling(
        self, resetter: KeyResetter, mock_db_pool, test_key
    ):
        """Тест обработки ошибки БД."""
        # Arrange
        mock_db_pool.execute = AsyncMock(
            side_effect=asyncpg.exceptions.PostgresError("Connection lost")
        )

        # Act & Assert
        with pytest.raises(asyncpg.exceptions.PostgresError):
            await resetter.reset_key_after_renewal(mock_db_pool, test_key)

    @pytest.mark.asyncio
    async def test_reset_key_cache_error_handling(
        self, resetter: KeyResetter, mock_db_pool, mock_cache_service, test_key
    ):
        """Тест обработки ошибки кеша (не критична, логгируется)."""
        # Arrange: кеш падает
        mock_cache_service.keys.set = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        # Act & Assert: ошибка пробрасывается
        with pytest.raises(Exception, match="Redis connection error"):
            await resetter.reset_key_after_renewal(mock_db_pool, test_key)

        # БД всё равно была обновлена
        mock_db_pool.execute.assert_called_once()


# Класс для будущих реальных интеграционных тестов с testcontainers
@pytest.mark.skip(
    reason="Требует запущенных PostgreSQL и Redis. Используйте testcontainers."
)
class TestResetterRealIntegration:
    """
    Реальные интеграционные тесты с PostgreSQL и Redis.
    
    Для запуска:
    1. Установить testcontainers: pip install testcontainers[postgres,redis]
    2. Запустить тесты: pytest -k TestResetterRealIntegration
    
    Пример фикстур:
    ```python
    @pytest.fixture
    def postgres_container():
        with PostgresContainer("postgres:15") as postgres:
            yield postgres
    
    @pytest.fixture
    def redis_container():
        with RedisContainer("redis:7") as redis:
            yield redis
    ```
    """

    @pytest.mark.asyncio
    async def test_real_database_reset(self):
        """Тест реального UPDATE в PostgreSQL."""
        pass

    @pytest.mark.asyncio
    async def test_real_cache_update(self):
        """Тест реального SET в Redis."""
        pass

    @pytest.mark.asyncio
    async def test_real_full_renewal_cycle(self):
        """Тест полного цикла с реальными БД и кешем."""
        pass
