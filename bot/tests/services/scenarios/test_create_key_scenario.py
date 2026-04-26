from unittest.mock import AsyncMock

import pytest
from aiogram_dialog import DialogManager

from config import DEFAULT_PRICING_PLAN
from models import Tariff, User, GiftLink
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario


class TestCreateFerstKeyScenario:
    @pytest.fixture
    async def mock_dialog_manager(self):
        manager = AsyncMock(spec=DialogManager)
        # Мокаем event.from_user.id
        manager.event.from_user.id = 123456
        return manager

    @pytest.fixture
    async def mock_cache(self):
        cache = AsyncMock()
        # Мокаем temporary_get для gifts
        cache.gifts.temporary_get = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    async def mock_model_data(self, mock_cache):
        model_data = AsyncMock()
        # Настраиваем мок для tariffs.get_data
        tariff = Tariff(
            id=1, name_tariff="Test Tariff", period=30, traffic_limit=10, limit_ip=2
        )
        model_data.tariffs.get_data = AsyncMock(return_value=tariff)
        return model_data

    @pytest.fixture
    async def mock_create_key(self):
        create_key = AsyncMock()
        create_key.create_key = AsyncMock(
            return_value={
                "public_link": "test_public_link",
                "link_to_connect": "https://test-connect.com",
                "email": "test@example.com",
            }
        )
        return create_key

    @pytest.fixture
    async def mock_gift_service(self):
        gift_service = AsyncMock()
        return gift_service

    @pytest.fixture
    async def mock_trial_user(self):
        trial_user = AsyncMock()
        trial_user.installation_trial = AsyncMock()
        return trial_user

    @pytest.fixture
    async def create_key_scenario(
        self,
        mock_cache,
        mock_model_data,
        mock_create_key,
        mock_gift_service,
        mock_dialog_manager,
        mock_trial_user,
        mock_conn,
    ):
        return CreateFerstKeyScenario(
            cache=mock_cache,
            model_data=mock_model_data,
            create_key=mock_create_key,
            gift_service=mock_gift_service,
            dialog_manager=mock_dialog_manager,
            trial_user=mock_trial_user,
            conn=mock_conn,
        )

    def test_create_key_scenario_initialization(
        self, create_key_scenario, mock_dialog_manager
    ):
        """Тест инициализации сценария создания ключа."""
        assert create_key_scenario.dialog_manager == mock_dialog_manager
        assert create_key_scenario.cache is not None
        assert create_key_scenario.tariff_data is not None
        assert create_key_scenario.user_data is not None
        assert create_key_scenario.create_key is not None
        assert create_key_scenario.gift_service is not None
        assert create_key_scenario.trial_user is not None

    async def test_create_key_scenario_get_data_no_gift(
        self, create_key_scenario, mock_cache, mock_model_data
    ):
        """Тест получения данных без подарка."""
        # Мокаем user_data.get_data
        user = User(tg_id=123456, trial=0, server_id=1)
        create_key_scenario.user_data.get_data = AsyncMock(return_value=user)

        # Выполняем get_data
        await create_key_scenario.get_data()

        # Проверяем, что данные пользователя установлены
        assert create_key_scenario._user == user
        assert create_key_scenario._gift is None

        # Проверяем, что tariff_id установлен в DEFAULT_PRICING_PLAN (как int)
        expected_tariff_id = int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10
        mock_model_data.tariffs.get_data.assert_called_once_with(expected_tariff_id)

        # Проверяем, что сессия установлена
        assert create_key_scenario._conn is not None

    async def test_create_key_scenario_get_data_with_gift(
        self, create_key_scenario, mock_cache, mock_model_data
    ):
        """Тест получения данных с подарком."""
        # Создаем мок для gift
        gift = GiftLink(sender_tg_id=654321, tariff_id=2, token="gift_token_123")

        # Настраиваем мок для temporary_get
        temp_data = {"gift": gift}
        mock_cache.gifts.temporary_get = AsyncMock(return_value=temp_data)

        # Мокаем user_data.get_data
        user = User(tg_id=123456, trial=0, server_id=1)
        create_key_scenario.user_data.get_data = AsyncMock(return_value=user)

        # Выполняем get_data
        await create_key_scenario.get_data()

        # Проверяем, что данные пользователя установлены
        assert create_key_scenario._user == user
