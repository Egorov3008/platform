"""ОТКЛЮЧЕН 2026-06-01: тест покрывает старую сигнатуру GiftActivationScenario
(service_model, ...). Текущая реализация работает через BackendAPIClient.
См. bot/.claude/CLAUDE.md — раздел "Removed from bot".
"""
import pytest  # noqa: F401
from unittest.mock import AsyncMock  # noqa: F401

from aiogram_dialog import StartMode  # noqa: F401

from models import GiftLink  # noqa: F401
from services.cache.key_manager import CacheKeyManager  # noqa: F401
from services.scenarios.gift_scenario import GiftActivationScenario  # noqa: F401
from states.gift import GiftStates  # noqa: F401
from states.instruction import Instruction  # noqa: F401

pytest.skip(
    "Legacy test for outdated GiftActivationScenario signature",
    allow_module_level=True,
)


def mock_dialog_manager_with_data(registration_result=None, middleware_data=None):
    dialog_manager = AsyncMock()
    dialog_manager.middleware_data = middleware_data or {}
    if registration_result:
        dialog_manager.middleware_data["registration_result"] = registration_result
    dialog_manager.event = AsyncMock()
    dialog_manager.event.from_user.id = 123456
    return dialog_manager


def mock_service_model():
    service_model = AsyncMock()
    service_model.gifts = AsyncMock()
    return service_model


def mock_saver():
    saver = AsyncMock()
    return saver


def mock_cache():
    cache = AsyncMock()
    cache.gifts = AsyncMock()
    return cache


class TestGiftActivationScenario:
    @pytest.fixture
    def dialog_manager(self):
        return mock_dialog_manager_with_data()

    @pytest.fixture
    def service_model(self):
        return mock_service_model()

    @pytest.fixture
    def saver(self):
        return mock_saver()

    @pytest.fixture
    def cache(self):
        return mock_cache()

    @pytest.fixture
    def scenario(self, dialog_manager, service_model, saver, cache):
        return GiftActivationScenario(
            dialog_manager=dialog_manager,
            service_model=service_model,
            saver=saver,
            cache=cache,
        )

    async def test_can_handle_no_registration_result(self, scenario, dialog_manager):
        # Arrange
        dialog_manager.middleware_data = {}

        # Act
        result = await scenario.can_handle()

        # Assert
        assert result is False
        assert scenario._token is None
        assert scenario._type is None

    async def test_can_handle_with_registration_result(self, scenario, dialog_manager):
        # Arrange
        registration_result = {"token": "test_token", "type": "gift"}
        dialog_manager.middleware_data["registration_result"] = registration_result

        # Act
        result = await scenario.can_handle()

        # Assert
        assert result is True
        assert scenario._token == "test_token"
        assert scenario._type == "gift"

    async def test_get_data_with_registration_result(self, scenario, dialog_manager):
        # Arrange
        registration_result = {"token": "test_token", "type": "gift"}
        session = AsyncMock()
        dialog_manager.middleware_data.update(
            {"registration_result": registration_result, "session": session}
        )

        # Act
        await scenario.get_data()

        # Assert
        assert scenario._token == "test_token"
        assert scenario._type == "gift"
        assert scenario._conn == session

    async def test_get_data_without_registration_result(self, scenario, dialog_manager):
        # Arrange
        dialog_manager.middleware_data = {}

        # Act
        await scenario.get_data()

        # Assert
        assert scenario._token is None
        assert scenario._type is None
        assert scenario._conn is None

    async def test_get_gift_with_token(self, scenario, service_model):
        # Arrange
        token = "test_token"
        expected_gift = AsyncMock(spec=GiftLink)
        service_model.gifts.get_by.return_value = expected_gift

        # Act
        result = await scenario._get_gift(token)

        # Assert
        assert result == expected_gift
        service_model.gifts.get_by.assert_called_once_with(token=token)

    async def test_get_gift_without_token(self, scenario):
        # Act & Assert
        with pytest.raises(ValueError, match="Токен не передан"):
            await scenario._get_gift(None)

    async def test_process_checked_gift_already_used(self, scenario, dialog_manager):
        # Arrange
        gift_link = AsyncMock(spec=GiftLink)
        gift_link.is_redeemable.return_value = False

        # Act
        await scenario._process_checked_gift(gift_link)

        # Assert
        dialog_manager.start.assert_called_once_with(
            GiftStates.already_used, mode=StartMode.RESET_STACK
        )

    async def test_process_checked_gift_redeemable(self, scenario, dialog_manager):
        # Arrange
        gift_link = AsyncMock(spec=GiftLink)
        gift_link.is_redeemable.return_value = True

        # Act
        await scenario._process_checked_gift(gift_link)

        # Assert
        dialog_manager.start.assert_not_called()

    async def test_process_success(self, scenario, saver, cache, dialog_manager):
        # Arrange
        from datetime import timedelta

        user_id = 123456
        gift = AsyncMock(spec=GiftLink)
        gift.tariff_id = 5

        # Act
        await scenario._process_success(user_id, gift)

        # Assert
        saver.register_user.assert_called_once_with(
            scenario._conn, tg_id=user_id, server_id=2
        )
        cache.gifts.temporary_set.assert_called_once_with(
            CacheKeyManager.gift_activation(user_id),
            ttl=timedelta(seconds=1800),
            gift_status=True,
            gift=gift,
        )
        dialog_manager.start.assert_called_once_with(
            Instruction.choosing_device, mode=StartMode.RESET_STACK
        )

    async def test_start_success_flow(
        self, scenario, dialog_manager, service_model, saver, cache
    ):
        # Arrange
        from datetime import timedelta

        user_id = 123456
        token = "test_token"
        gift = AsyncMock(spec=GiftLink)
        gift.is_redeemable.return_value = True
        gift.tariff_id = 5

        registration_result = {"token": token, "type": "gift"}
        session = AsyncMock()
        dialog_manager.middleware_data.update(
            {"registration_result": registration_result, "session": session}
        )
        service_model.gifts.get_by.return_value = gift
        cache.gifts.temporary_set.return_value = True

        # Act
        await scenario.can_handle()
        await scenario.start()

        # Assert
        # Проверяем, что данные извлечены
        assert scenario._token == token
        assert scenario._type == "gift"
        assert scenario._conn == session

        # Проверяем получение подарка
        service_model.gifts.get_by.assert_called_once_with(token=token)

        # Проверяем успешную обработку
        saver.register_user.assert_called_once_with(session, tg_id=user_id, server_id=2)

        cache.gifts.temporary_set.assert_called_once_with(
            CacheKeyManager.gift_activation(user_id),
            ttl=timedelta(seconds=1800),
            gift_status=True,
            gift=gift,
        )
        dialog_manager.start.assert_called_once_with(
            Instruction.choosing_device, mode=StartMode.RESET_STACK
        )

    async def test_start_gift_not_redeemable(
        self, scenario, dialog_manager, service_model
    ):
        """Тестирует ситуацию, когда подарок уже использован."""
        # Arrange
        token = "test_token"
        gift = AsyncMock(spec=GiftLink)
        gift.is_redeemable.return_value = False

        registration_result = {"token": token, "type": "gift"}
        dialog_manager.middleware_data["registration_result"] = registration_result
        service_model.gifts.get_by.return_value = gift

        # Act
        await scenario.can_handle()
        await scenario.start()

        # Assert
        service_model.gifts.get_by.assert_called_once_with(token=token)
        dialog_manager.start.assert_called_once_with(
            GiftStates.already_used, mode=StartMode.RESET_STACK
        )

    async def test_start_exception_handling(
        self, scenario, dialog_manager, service_model, caplog
    ):
        # Arrange
        token = "test_token"

        registration_result = {"token": token, "type": "gift"}
        dialog_manager.middleware_data["registration_result"] = registration_result
        service_model.gifts.get_by.side_effect = Exception("Database error")

        # Act
        await scenario.start()

        # Assert
        dialog_manager.start.assert_called_once_with(GiftStates.error)
