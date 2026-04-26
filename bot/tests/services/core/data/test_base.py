from unittest.mock import AsyncMock, Mock

import pytest

from models import User
from services.core.data.base import BaseData


def create_mock_cache_service():
    """Создает мок CacheService с подсистемой users (для модели User)."""
    cache_service = AsyncMock()
    cache_service.users = AsyncMock()
    cache_service.users.get = AsyncMock()
    cache_service.users.all = AsyncMock()
    cache_service.users.set = AsyncMock(return_value=True)
    cache_service.users.delete = AsyncMock(return_value=True)
    return cache_service


def create_mock_service_data():
    """Создает мок репозитория данных."""
    service = AsyncMock()
    service.create = AsyncMock()
    service.delete = AsyncMock()
    service.update = AsyncMock()
    return service


@pytest.fixture
async def base_data():
    """Фикстура BaseData с моделью User (model_name='user')."""
    cache_service = create_mock_cache_service()
    service_data = create_mock_service_data()
    return BaseData(User, cache_service, service_data)


class TestBaseData:
    """Тесты для класса BaseData"""

    async def test_get_data_success(self, base_data):
        """Тест успешного получения данных"""
        mock_obj = Mock()
        base_data.cache_service.users.get.return_value = mock_obj

        result = await base_data.get_data(123)

        assert result == mock_obj
        base_data.cache_service.users.get.assert_called_once_with("user_123")

    async def test_get_data_no_identifier(self, base_data):
        """Тест поведения при отсутствии идентификатора"""
        result = await base_data.get_data(None)

        assert result is None
        base_data.cache_service.users.get.assert_not_called()

    async def test_get_data_not_found(self, base_data):
        """Тест поведения когда объект не найден в кэше"""
        base_data.cache_service.users.get.return_value = None

        result = await base_data.get_data(123)

        assert result is None
        base_data.cache_service.users.get.assert_called_once_with("user_123")

    async def test_get_all(self, base_data):
        """Тест получения всех объектов"""
        mock_objects = [AsyncMock(), AsyncMock()]
        base_data.cache_service.users.all.return_value = mock_objects

        result = await base_data.get_all()

        assert result == mock_objects
        base_data.cache_service.users.all.assert_called_once()

    async def test_exists_true(self, base_data):
        """Тест проверки существования объекта (объект существует)"""
        mock_obj = Mock()
        base_data.cache_service.users.get.return_value = mock_obj

        result = await base_data.exists(123)

        assert result is True
        base_data.cache_service.users.get.assert_called_once_with("user_123")

    async def test_exists_false(self, base_data):
        """Тест проверки существования объекта (объект не существует)"""
        base_data.cache_service.users.get.return_value = None

        result = await base_data.exists(123)

        assert result is False
        base_data.cache_service.users.get.assert_called_once_with("user_123")

    async def test_count(self, base_data):
        """Тест подсчета количества объектов"""
        mock_objects = [Mock(), Mock()]
        base_data.cache_service.users.all.return_value = mock_objects

        result = await base_data.count()

        assert result == 2
        base_data.cache_service.users.all.assert_called_once()

    async def test_save_data(self, base_data):
        """Тест сохранения данных"""
        mock_data = Mock()
        mock_data.tg_id = 123
        mock_data.to_dict.return_value = {"tg_id": 123, "username": "test"}
        mock_conn = AsyncMock()

        await base_data.save_data(mock_conn, mock_data, tg_id=123)

        base_data.service.create.assert_called_once_with(
            mock_conn, tg_id=123, username="test"
        )
        base_data.cache_service.users.set.assert_called_once_with("user_123", mock_data)

    async def test_delete_data(self, base_data):
        """Тест удаления данных"""
        mock_data = Mock()
        mock_data.tg_id = 123
        mock_data.to_dict.return_value = {"tg_id": 123, "username": "test"}
        mock_conn = AsyncMock()

        await base_data.delete_data(mock_conn, mock_data)

        base_data.service.delete.assert_called_once_with(
            mock_conn, tg_id=123, username="test"
        )
        base_data.cache_service.users.delete.assert_called_once_with("user_123")

    async def test_get_by_single_match(self, base_data):
        """Тест получения по атрибуту (одно совпадение) — возвращает объект, не список"""
        mock_obj1 = Mock()
        mock_obj1.email = "test1@example.com"
        mock_obj2 = Mock()
        mock_obj2.email = "test2@example.com"
        base_data.cache_service.users.all.return_value = [mock_obj1, mock_obj2]

        result = await base_data.get_by(email="test1@example.com")

        assert result == mock_obj1
        base_data.cache_service.users.all.assert_called_once()

    async def test_get_by_multiple_match(self, base_data):
        """Тест получения по атрибуту (несколько совпадений) — возвращает список"""
        mock_obj1 = Mock()
        mock_obj1.status = "active"
        mock_obj2 = Mock()
        mock_obj2.status = "active"
        mock_obj3 = Mock()
        mock_obj3.status = "inactive"
        base_data.cache_service.users.all.return_value = [
            mock_obj1,
            mock_obj2,
            mock_obj3,
        ]

        result = await base_data.get_by(status="active")

        assert len(result) == 2
        assert mock_obj1 in result
        assert mock_obj2 in result
        assert mock_obj3 not in result
        base_data.cache_service.users.all.assert_called_once()

    async def test_get_by_no_match(self, base_data):
        """Тест получения по атрибуту (нет совпадений) — возвращает None"""
        mock_obj1 = Mock()
        mock_obj1.email = "test1@example.com"
        mock_obj2 = Mock()
        mock_obj2.email = "test2@example.com"
        base_data.cache_service.users.all.return_value = [mock_obj1, mock_obj2]

        result = await base_data.get_by(email="notfound@example.com")

        assert result is None
        base_data.cache_service.users.all.assert_called_once()

    async def test_get_by_empty_cache(self, base_data):
        """Тест получения по атрибуту при пустом кэше — возвращает пустой список"""
        base_data.cache_service.users.all.return_value = []

        result = await base_data.get_by(status="active")

        assert result == []
        base_data.cache_service.users.all.assert_called_once()

    async def test_update(self, base_data):
        """Тест обновления данных"""
        mock_data = Mock()
        mock_data.tg_id = 123
        mock_data.to_dict.return_value = {"tg_id": 123, "username": "updated"}
        mock_conn = AsyncMock()
        search_data = {"tg_id": 123}

        await base_data.update(mock_conn, mock_data, search_data)

        base_data.service.update.assert_called_once_with(
            mock_conn, search_data, tg_id=123, username="updated"
        )
        base_data.cache_service.users.set.assert_called_once_with("user_123", mock_data)
