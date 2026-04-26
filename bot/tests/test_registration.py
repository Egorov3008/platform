from unittest.mock import AsyncMock

import pytest

from registration.base_registration import BaseRegistration
from registration.gift_registration import GiftRegistration
from registration.registration_factory import RegistrationFactory
from services.core.data.service import ServiceDataModel


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=ServiceDataModel)
    service.gifts = AsyncMock()
    return service


@pytest.fixture
def gift_registration(mock_service):
    registration = GiftRegistration(mock_service)
    registration._gift_data = mock_service.gifts
    return registration


class TestBaseRegistration:
    """
    Тесты для абстрактного класса BaseRegistration
    """


class TestGiftRegistration:
    """Тесты для GiftRegistration"""

    async def test_can_handle_returns_true_for_redeemable_gift(
        self, gift_registration, mock_service, gift_link
    ):
        """Проверяет, что can_handle возвращает True для подарка, который можно использовать"""

        gift_link._status = "active"
        mock_service.gifts.get_by.return_value = gift_link

        result = await gift_registration.can_handle("test_token")

        mock_service.gifts.get_by.assert_called_once_with(token="test_token")
        assert result is True

    async def test_can_handle_returns_false_for_non_redeemable_gift(
        self, gift_registration, mock_service, gift_link
    ):
        """Проверяет, что can_handle возвращает False для подарка, который нельзя использовать"""

        gift_link._status = "redeemed"
        mock_service.gifts.get_by.return_value = gift_link

        result = await gift_registration.can_handle("test_token")

        mock_service.gifts.get_by.assert_called_once_with(token="test_token")
        assert result is False

    async def test_can_handle_returns_false_when_gift_not_found(
        self, gift_registration, mock_service
    ):
        """Проверяет, что can_handle возвращает False, когда подарок не найден"""
        mock_service.gifts.get_by.return_value = None

        result = await gift_registration.can_handle("test_token")

        mock_service.gifts.get_by.assert_called_once_with(token="test_token")
        assert result is False

    async def test_register_returns_success_for_valid_gift(
        self, gift_registration, mock_conn, mock_service, gift_link
    ):
        """Проверяет, что register возвращает успешный результат для валидного подарка"""
        # Устанавливаем мок кеша в экземпляр
        gift_registration.service = mock_service
        mock_service.gifts.get_by.return_value = gift_link

        expected_result = {
            "success": True,
            "type": "gift",
            "token": "test_token",
            "tariff_id": 1,
            "from_user_id": 123,
        }

        result = await gift_registration.register("test_token")

        mock_service.gifts.get_by.assert_called_once_with(token="test_token")
        assert result == expected_result

    async def test_register_returns_error_when_gift_not_found(
        self, gift_registration, caplog, mock_service
    ):
        """Проверяет, что register возвращает ошибку, когда подарок не найден"""
        # Настройка моков

        gift_registration.service = mock_service
        mock_service.gifts.get_by.return_value = None

        expected_result = {"success": False, "error": "gift_link_not_found"}

        result = await gift_registration.register("invalid_token")

        mock_service.gifts.get_by.assert_called_once_with(token="invalid_token")
        assert result == expected_result


class TestRegistrationFactory:
    """
    Тесты для RegistrationFactory
    """

    @pytest.fixture
    def factory(self):
        return RegistrationFactory()

    @pytest.fixture
    def mock_handler(self):
        handler = AsyncMock(spec=BaseRegistration)
        handler.can_handle = AsyncMock(return_value=True)
        handler.register = AsyncMock(return_value={"success": True, "type": "test"})
        return handler

    def test_factory_initialization(self, factory):
        """Проверяет инициализацию фабрики"""
        assert isinstance(factory._handlers, list)
        assert len(factory._handlers) == 0

    def test_register_handler_adds_handler(self, factory, mock_handler):
        """Проверяет, что register_handler добавляет обработчик в список"""
        factory.register_handler(mock_handler)

        assert len(factory._handlers) == 1
        assert factory._handlers[0] == mock_handler

    async def test_handle_registration_calls_can_handle_on_handlers(
        self, factory, mock_handler
    ):
        """Проверяет, что handle_registration вызывает can_handle на обработчиках"""
        factory.register_handler(mock_handler)

        await factory.handle_registration("test_token")

        mock_handler.can_handle.assert_called_once_with("test_token")

    async def test_handle_registration_calls_register_on_matching_handler(
        self, factory, mock_handler
    ):
        """Проверяет, что handle_registration вызывает register на подходящем обработчике"""
        factory.register_handler(mock_handler)

        await factory.handle_registration("test_token")

        mock_handler.register.assert_called_once_with("test_token")

    async def test_handle_registration_returns_handler_result(
        self, factory, mock_handler
    ):
        """Проверяет, что handle_registration возвращает результат обработчика"""
        expected_result = {"success": True, "type": "test"}
        mock_handler.register.return_value = expected_result
        factory.register_handler(mock_handler)

        result = await factory.handle_registration("test_token")

        assert result == expected_result

    async def test_handle_registration_returns_unknown_user_when_handler_found(
        self, factory, mock_handler
    ):
        """Проверяет, что handle_registration возвращает unknown_user, когда найден обработчик"""
        # Настройка: can_handle возвращает True
        mock_handler.can_handle.return_value = True
        factory.register_handler(mock_handler)

        result = await factory.handle_registration("test_token")

        # Проверяем, что возвращается результат register, а не unknown_user
        assert result["success"] is True
        assert result["type"] == "test"

    async def test_handle_registration_returns_unknown_token_when_no_handlers_match(
        self, factory
    ):
        """Проверяет, что handle_registration возвращает unknown_token, когда ни один обработчик не подходит"""
        # Создаем обработчик, который не может обработать токен
        mock_handler = AsyncMock(spec=BaseRegistration)
        mock_handler.can_handle = AsyncMock(return_value=False)

        factory.register_handler(mock_handler)

        expected_result = {"success": True, "type": "unknown_user"}
        result = await factory.handle_registration("unknown_token")

        assert result == expected_result
