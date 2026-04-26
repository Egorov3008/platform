import pytest
from unittest.mock import AsyncMock

from services.core.data.service import ServiceDataModel


@pytest.fixture
async def mock_cache_service():
    """Фикстура для мока сервиса кэша"""
    cache = AsyncMock()
    cache.users = AsyncMock()
    cache.keys = AsyncMock()
    cache.servers = AsyncMock()
    cache.inbounds = AsyncMock()
    cache.payments = AsyncMock()
    cache.gifts = AsyncMock()
    cache.tariffs = AsyncMock()
    return cache


@pytest.fixture
async def mock_data_service():
    """Фикстура для мока сервиса данных"""
    service = AsyncMock()
    service.users = AsyncMock()
    service.keys = AsyncMock()
    service.servers = AsyncMock()
    service.inbounds = AsyncMock()
    service.payments = AsyncMock()
    service.gifts = AsyncMock()
    service.tariffs = AsyncMock()
    return service


@pytest.fixture
async def service_data_model(mock_cache_service, mock_data_service):
    """Фикстура для создания экземпляра ServiceDataModel"""
    return ServiceDataModel(mock_cache_service, mock_data_service)


class TestServiceDataModel:
    """Тесты для класса ServiceDataModel"""

    async def test_initialization(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест инициализации ServiceDataModel"""
        # Проверяем, что атрибуты инициализированы правильно
        assert service_data_model.cache_service == mock_cache_service
        assert service_data_model.data_service == mock_data_service

    async def test_users_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства users"""
        # Проверяем, что свойство users инициализировано как BaseData
        assert hasattr(service_data_model, "users")
        assert service_data_model.users is not None
        # Проверяем, что переданы правильные аргументы
        # (здесь мы не можем напрямую проверить тип, но можем проверить наличие атрибутов)
        assert hasattr(service_data_model.users, "cache_service")
        assert hasattr(service_data_model.users, "service")
        assert service_data_model.users.cache_service == mock_cache_service
        assert service_data_model.users.service == mock_data_service.users

    async def test_keys_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства keys"""
        # Проверяем, что свойство keys инициализировано как BaseData
        assert hasattr(service_data_model, "keys")
        assert service_data_model.keys is not None
        assert hasattr(service_data_model.keys, "cache_service")
        assert hasattr(service_data_model.keys, "service")
        assert service_data_model.keys.cache_service == mock_cache_service
        assert service_data_model.keys.service == mock_data_service.keys

    async def test_server_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства servers"""
        # Проверяем, что свойство servers инициализировано как BaseData
        assert hasattr(service_data_model, "servers")
        assert service_data_model.servers is not None
        assert hasattr(service_data_model.servers, "cache_service")
        assert hasattr(service_data_model.servers, "service")
        assert service_data_model.servers.cache_service == mock_cache_service
        assert service_data_model.servers.service == mock_data_service.servers

    async def test_inbounds_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства inbounds"""
        # Проверяем, что свойство inbounds инициализировано как BaseData
        assert hasattr(service_data_model, "inbounds")
        assert service_data_model.inbounds is not None
        assert hasattr(service_data_model.inbounds, "cache_service")
        assert hasattr(service_data_model.inbounds, "service")
        assert service_data_model.inbounds.cache_service == mock_cache_service
        assert service_data_model.inbounds.service == mock_data_service.inbounds

    async def test_payment_class_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства payments"""
        # Проверяем, что свойство payments инициализировано как BaseData
        assert hasattr(service_data_model, "payments")
        assert service_data_model.payments is not None
        assert hasattr(service_data_model.payments, "cache_service")
        assert hasattr(service_data_model.payments, "service")
        assert service_data_model.payments.cache_service == mock_cache_service
        assert service_data_model.payments.service == mock_data_service.payments

    async def test_gifts_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства gifts"""
        # Проверяем, что свойство gifts инициализировано как BaseData
        assert hasattr(service_data_model, "gifts")
        assert service_data_model.gifts is not None
        assert hasattr(service_data_model.gifts, "cache_service")
        assert hasattr(service_data_model.gifts, "service")
        assert service_data_model.gifts.cache_service == mock_cache_service
        assert service_data_model.gifts.service == mock_data_service.gifts

    async def test_tariffs_property(
        self, service_data_model, mock_cache_service, mock_data_service
    ):
        """Тест свойства tariffs"""
        # Проверяем, что свойство tariffs инициализировано как BaseData
        assert hasattr(service_data_model, "tariffs")
        assert service_data_model.tariffs is not None
        assert hasattr(service_data_model.tariffs, "cache_service")
        assert hasattr(service_data_model.tariffs, "service")
        assert service_data_model.tariffs.cache_service == mock_cache_service
        assert service_data_model.tariffs.service == mock_data_service.tariffs
