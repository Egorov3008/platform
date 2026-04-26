import pytest
from unittest.mock import AsyncMock, MagicMock

from database.base import BaseRepository
from database.service import DataService


class TestBaseRepository:
    """Тесты для базового репозитория."""

    @pytest.fixture
    def mock_pool(self):
        return AsyncMock()

    @pytest.fixture
    def mock_model(self):
        model = MagicMock()
        model.__name__ = "MockModel"
        return model

    @pytest.fixture
    def repository(self, mock_model):
        return BaseRepository("test_table", mock_model)

    async def test_get_success(self, repository, mock_pool):
        """Тест успешного получения записи."""
        # Arrange
        mock_record = {"id": 1, "name": "test"}
        mock_pool.fetchrow.return_value = mock_record
        repository.model.return_value = mock_record

        # Act
        result = await repository.get(mock_pool, id=1)

        # Assert
        assert result == mock_record
        mock_pool.fetchrow.assert_called_once()

    async def test_get_not_found(self, repository, mock_pool):
        """Тест получения несуществующей записи."""
        # Arrange
        mock_pool.fetchrow.return_value = None

        # Act
        result = await repository.get(mock_pool, id=999)

        # Assert
        assert result is None
        mock_pool.fetchrow.assert_called_once()

    async def test_get_all_success(self, repository, mock_pool):
        """Тест получения всех записей."""
        # Arrange
        mock_records = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_pool.fetch.return_value = mock_records
        repository.model.side_effect = lambda **kwargs: kwargs

        # Act
        result = await repository.get_all(mock_pool)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        mock_pool.fetch.assert_called_once()

    async def test_delete_success(self, repository, mock_pool):
        """Тест успешного удаления записи."""
        # Arrange
        mock_pool.execute.return_value = "DELETE 1"

        # Act
        result = await repository.delete(mock_pool, id=1)

        # Assert
        assert result is True
        mock_pool.execute.assert_called_once()

    async def test_delete_not_found(self, repository, mock_pool):
        """Тест удаления несуществующей записи."""
        # Arrange
        mock_pool.execute.return_value = "DELETE 0"

        # Act
        result = await repository.delete(mock_pool, id=999)

        # Assert
        assert result is False
        mock_pool.execute.assert_called_once()

    async def test_create_success(self, repository, mock_pool):
        """Тест успешного создания записи."""
        # Arrange
        mock_pool.execute.return_value = "INSERT 1"
        data = {"name": "test", "value": "data"}

        # Act
        result = await repository.create(mock_pool, **data)

        # Assert
        assert result is True
        mock_pool.execute.assert_called_once()

    async def test_create_failure(self, repository, mock_pool):
        """Тест неудачного создания записи."""
        # Arrange
        mock_pool.execute.return_value = "INSERT 0"
        data = {"name": "test", "value": "data"}

        # Act
        result = await repository.create(mock_pool, **data)

        # Assert
        assert result is False
        mock_pool.execute.assert_called_once()

    async def test_update_success(self, repository, mock_pool):
        """Тест успешного обновления записи."""
        # Arrange
        mock_pool.execute.return_value = "UPDATE 1"
        search_data = {"id": 1}
        update_data = {"name": "updated"}

        # Act
        result = await repository.update(mock_pool, search_data, **update_data)

        # Assert
        assert result is True
        mock_pool.execute.assert_called_once()

    async def test_update_failure(self, repository, mock_pool):
        """Тест неудачного обновления записи."""
        # Arrange
        mock_pool.execute.return_value = "UPDATE 0"
        search_data = {"id": 999}
        update_data = {"name": "updated"}

        # Act
        result = await repository.update(mock_pool, search_data, **update_data)

        # Assert
        assert result is False
        mock_pool.execute.assert_called_once()


class TestDataServiceRepositories:
    """Тесты для репозиториев DataService."""

    @pytest.fixture
    def data_service(self):
        return DataService()

    @pytest.fixture
    def mock_pool(self):
        return AsyncMock()

    def test_data_service_has_all_repositories(self, data_service):
        """Тест наличия всех репозиториев в DataService."""
        assert hasattr(data_service, "users")
        assert hasattr(data_service, "keys")
        assert hasattr(data_service, "servers")
        assert hasattr(data_service, "payments")
        assert hasattr(data_service, "tariffs")
        assert hasattr(data_service, "inbounds")

    async def test_users_repository_crud(self, data_service, mock_pool, mock_user):
        """Тест операций CRUD для репозитория users."""
        repo = data_service.users

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_user.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_user)
        result = await repo.get(mock_pool, tg_id=mock_user.tg_id)
        assert result == mock_user

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_user])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_user

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(mock_pool, {"tg_id": mock_user.tg_id}, username="updated")
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, tg_id=mock_user.tg_id)
        repo.delete.assert_called_once()

    async def test_keys_repository_crud(self, data_service, mock_pool, mock_key):
        """Тест операций CRUD для репозитория keys."""
        repo = data_service.keys

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_key.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_key)
        result = await repo.get(mock_pool, tg_id=mock_key.tg_id)
        assert result == mock_key

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_key])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_key

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(mock_pool, {"tg_id": mock_key.tg_id}, notified_24h=True)
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, tg_id=mock_key.tg_id)
        repo.delete.assert_called_once()

    async def test_servers_repository_crud(self, data_service, mock_pool, mock_server):
        """Тест операций CRUD для репозитория servers."""
        repo = data_service.servers

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_server.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_server)
        result = await repo.get(mock_pool, id=mock_server.id)
        assert result == mock_server

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_server])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_server

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(mock_pool, {"id": mock_server.id}, server_name="updated")
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, id=mock_server.id)
        repo.delete.assert_called_once()

    async def test_payments_repository_crud(
        self, data_service, mock_pool, mock_payment
    ):
        """Тест операций CRUD для репозитория payments."""
        repo = data_service.payments

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_payment.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_payment)
        result = await repo.get(mock_pool, payment_id=mock_payment.payment_id)
        assert result == mock_payment

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_payment])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_payment

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(
            mock_pool, {"payment_id": mock_payment.payment_id}, status="processed"
        )
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, payment_id=mock_payment.payment_id)
        repo.delete.assert_called_once()

    async def test_tariffs_repository_crud(self, data_service, mock_pool, mock_tariff):
        """Тест операций CRUD для репозитория tariffs."""
        repo = data_service.tariffs

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_tariff.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_tariff)
        result = await repo.get(mock_pool, id=mock_tariff.id)
        assert result == mock_tariff

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_tariff])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_tariff

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(mock_pool, {"id": mock_tariff.id}, name_tariff="updated")
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, id=mock_tariff.id)
        repo.delete.assert_called_once()

    async def test_inbounds_repository_crud(
        self, data_service, mock_pool, mock_inbound_full
    ):
        """Тест операций CRUD для репозитория inbounds."""
        repo = data_service.inbounds

        # Test create
        repo.create = AsyncMock(return_value=True)
        await repo.create(mock_pool, **mock_inbound_full.to_dict())
        repo.create.assert_called_once()

        # Test get
        repo.get = AsyncMock(return_value=mock_inbound_full)
        result = await repo.get(mock_pool, inbound_id=mock_inbound_full.inbound_id)
        assert result == mock_inbound_full

        # Test get_all
        repo.get_all = AsyncMock(return_value=[mock_inbound_full])
        results = await repo.get_all(mock_pool)
        assert len(results) == 1
        assert results[0] == mock_inbound_full

        # Test update
        repo.update = AsyncMock(return_value=True)
        await repo.update(
            mock_pool,
            {"inbound_id": mock_inbound_full.inbound_id},
            name_inbound="updated",
        )
        repo.update.assert_called_once()

        # Test delete
        repo.delete = AsyncMock(return_value=True)
        await repo.delete(mock_pool, inbound_id=mock_inbound_full.inbound_id)
        repo.delete.assert_called_once()
