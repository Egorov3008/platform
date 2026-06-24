from database.service import DataService
from database.base import BaseRepository


def test_data_service_initialization():
    """Тест инициализации DataService и создания репозиториев."""
    service = DataService()

    # Проверяем, что все атрибуты инициализированы
    assert hasattr(service, "users")
    assert hasattr(service, "keys")
    assert hasattr(service, "servers")
    assert hasattr(service, "payments")
    assert hasattr(service, "tariffs")

    # Проверяем, что они являются экземплярами BaseRepository
    assert isinstance(service.users, BaseRepository)
    assert isinstance(service.keys, BaseRepository)
    assert isinstance(service.servers, BaseRepository)
    assert isinstance(service.payments, BaseRepository)
    assert isinstance(service.tariffs, BaseRepository)

    # Проверяем соответствие таблиц и моделей
    assert service.users.table_name == "users"
    assert service.keys.table_name == "keys"
    assert service.servers.table_name == "servers"
    assert service.payments.table_name == "payments"
    assert service.tariffs.table_name == "tariff"
