from unittest.mock import AsyncMock, MagicMock

import pytest

from services.core.data.service import ServiceDataModel
from services.core.user.utils.saturation import SaturationUser


@pytest.fixture
def mock_model_data():
    model_data = MagicMock(spec=ServiceDataModel)
    model_data.servers = AsyncMock()
    model_data.users = AsyncMock()
    return model_data


@pytest.fixture
def build_saturation_user(mock_model_data):
    return SaturationUser(model_data=mock_model_data)


class TestSaturationUserRepository:
    def test_saturation_user_init(self, mock_model_data, build_saturation_user):
        """Тест инициализации класса SaturationUser."""
        assert build_saturation_user.server == mock_model_data.servers
        assert build_saturation_user.user_data == mock_model_data.users

    @pytest.mark.asyncio
    async def test_saturation_user_refresh_success(
        self, mock_model_data, user, server, build_saturation_user
    ):
        """Тест успешного обновления данных пользователя."""
        tg_id = 123
        build_saturation_user.user_data.get_data = AsyncMock(return_value=user)
        build_saturation_user.server.get_data = AsyncMock(return_value=server)
        build_saturation_user.user_data.get_by = AsyncMock(
            return_value=["key1", "key2"]
        )

        result = await build_saturation_user.refresh(tg_id)

        assert result["user"] == user
        assert result["connect_module"] == server
        assert result["keys"] == ["key1", "key2"]

        build_saturation_user.user_data.get_data.assert_called_once_with(tg_id)
        build_saturation_user.server.get_data.assert_called_once_with(user.server_id)
        build_saturation_user.user_data.get_by.assert_called_once_with(tg_id=tg_id)

    @pytest.mark.asyncio
    async def test_saturation_user_refresh_no_user(self, build_saturation_user):
        """Тест обновления данных при отсутствии пользователя."""
        tg_id = 123
        build_saturation_user.user_data.get_data = AsyncMock(return_value=None)

        result = await build_saturation_user.refresh(tg_id)

        assert result == {}

        build_saturation_user.user_data.get_data.assert_called_once_with(tg_id)

    @pytest.mark.asyncio
    async def test_get_data_for_users_success(self, build_saturation_user, user):
        """Тест успешного получения данных для пользователей."""
        # Настраиваем моки
        users = [user, user]  # Предполагаем, что user уже определен в фикстурах
        build_saturation_user.user_data.get_all = AsyncMock(return_value=users)
        build_saturation_user.refresh = AsyncMock(
            side_effect=[
                {"user": user, "connect_module": {}, "keys": ["key1"]},
                {"user": user, "connect_module": {}, "keys": ["key2"]},
            ]
        )

        # Выполняем метод
        result = await build_saturation_user.get_data_for_users()

        # Проверяем результат
        assert len(result) == 2
        assert result[0]["user"] == user
        assert result[0]["connect_module"] == {}
        assert result[0]["keys"] == ["key1"]
        assert result[1]["user"] == user
        assert result[1]["connect_module"] == {}
        assert result[1]["keys"] == ["key2"]
        assert build_saturation_user.user_data.get_all.called
        assert build_saturation_user.refresh.call_count == 2

    @pytest.mark.asyncio
    async def test_get_data_for_users_no_users(self, build_saturation_user):
        """Тест получения данных, когда нет пользователей."""
        # Настраиваем моки
        build_saturation_user.user_data.get_all = AsyncMock(return_value=[])

        # Выполняем метод
        result = await build_saturation_user.get_data_for_users()

        # Проверяем результат
        assert result == []
        assert build_saturation_user.user_data.get_all.called

    @pytest.mark.asyncio
    async def test_get_data_for_users_with_exception(self, build_saturation_user, user):
        """Тест обработки исключения при получении данных пользователей."""
        # Настраиваем моки
        users = [user]
        build_saturation_user.user_data.get_all = AsyncMock(return_value=users)
        build_saturation_user.refresh = AsyncMock(
            side_effect=Exception("Test exception")
        )

        # Выполняем метод
        result = await build_saturation_user.get_data_for_users()

        # Проверяем результат
        assert result == []
        assert build_saturation_user.user_data.get_all.called
        assert build_saturation_user.refresh.called
