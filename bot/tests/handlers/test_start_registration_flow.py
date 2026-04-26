"""
Comprehensive async tests for handlers/start.py — send_massage_registration.

Covers: unknown_user, gift, and registered_user routing branches,
proper dialog starts, missing registration_result fallback, AttributeError branch.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram_dialog import StartMode

from states.main import MainMenu
from states.registrate import Register


def _make_manager(middleware_data: dict | None = None) -> AsyncMock:
    manager = AsyncMock()
    manager.middleware_data = middleware_data or {}
    manager.event = AsyncMock()
    manager.event.from_user = AsyncMock()
    manager.event.from_user.id = 123456
    return manager


def _make_message(tg_id: int = 123456) -> AsyncMock:
    msg = AsyncMock()
    msg.from_user = AsyncMock()
    msg.from_user.id = tg_id
    return msg


class TestSendMassegeRegistration:
    async def test_unknown_user_starts_register_dialog(self):
        from handlers.start import send_massage_registration

        manager = _make_manager({"registration_result": {"type": "unknown_user"}})
        message = _make_message()

        await send_massage_registration(message, manager)

        manager.start.assert_called_once_with(Register.captcha, mode=StartMode.RESET_STACK)

    async def test_no_registration_result_starts_register_dialog(self):
        """Handler defaults to Register.captcha when registration_result is None."""
        from handlers.start import send_massage_registration

        manager = _make_manager({})
        message = _make_message()

        await send_massage_registration(message, manager)

        manager.start.assert_called_once_with(Register.captcha, mode=StartMode.RESET_STACK)

    async def test_registered_user_goes_to_main_menu(self):
        from handlers.start import send_massage_registration

        manager = _make_manager({"registration_result": {"type": "registered_user"}})
        message = _make_message()

        await send_massage_registration(message, manager)

        manager.start.assert_called_once_with(MainMenu.main, mode=StartMode.RESET_STACK)

    async def test_gift_registration_creates_and_starts_scenario(self):
        """Gift type resolves dependencies, creates GiftActivationScenario, calls start()."""
        from unittest.mock import patch
        from handlers.start import send_massage_registration

        service_model = AsyncMock()
        saver = AsyncMock()
        cache = AsyncMock()

        def _resolve(cls):
            from services.core.data.service import ServiceDataModel
            from services.core.user.utils.saver import SeverUser
            if cls is ServiceDataModel:
                return service_model
            if cls is SeverUser:
                return saver
            return AsyncMock()

        container = MagicMock()
        container.resolve = MagicMock(side_effect=_resolve)

        registration_result = {
            "type": "gift",
            "token": "abc123",
            "tariff_id": 2,
            "from_user_id": 77,
        }
        manager = _make_manager({
            "registration_result": registration_result,
            "container": container,
            "cache": cache,
        })
        message = _make_message()

        gift_scenario_mock = AsyncMock()
        gift_scenario_mock.start = AsyncMock()

        with patch("handlers.start.GiftActivationScenario", return_value=gift_scenario_mock):
            await send_massage_registration(message, manager)

        gift_scenario_mock.start.assert_called_once()

    async def test_registration_result_injected_in_middleware_data(self):
        """registration_result is read from middleware_data correctly."""
        from handlers.start import send_massage_registration

        reg_result = {"type": "registered_user", "success": True}
        manager = _make_manager({"registration_result": reg_result})
        message = _make_message()

        await send_massage_registration(message, manager)

        # Verify the handler read the right type
        manager.start.assert_called_once_with(MainMenu.main, mode=StartMode.RESET_STACK)

    async def test_unknown_type_raises_attribute_error(self):
        """Unknown type in registration_result raises AttributeError."""
        from handlers.start import send_massage_registration

        manager = _make_manager({"registration_result": {"type": "completely_unknown"}})
        message = _make_message()

        with pytest.raises(AttributeError):
            await send_massage_registration(message, manager)


class TestSendMassegeUserStart:
    """Tests for /profile handler — send_massage_user_start."""

    async def test_unregistered_user_redirected_to_register(self):
        from handlers.start import send_massage_user_start

        cache = AsyncMock()
        cache.users.get = AsyncMock(return_value=None)
        manager = _make_manager({"cache": cache})
        message = _make_message(tg_id=999)

        await send_massage_user_start(message, manager)

        manager.start.assert_called_once_with(Register.captcha, mode=StartMode.RESET_STACK)

    async def test_user_with_trial_zero_goes_to_welcome(self):
        from handlers.start import send_massage_user_start
        from models import User

        user = User(tg_id=999, trial=0)
        cache = AsyncMock()
        cache.users.get = AsyncMock(return_value=user)
        manager = _make_manager({"cache": cache})
        message = _make_message(tg_id=999)

        await send_massage_user_start(message, manager)

        manager.start.assert_called_once_with(MainMenu.welcome, mode=StartMode.RESET_STACK)

    async def test_user_with_trial_nonzero_goes_to_main(self):
        from handlers.start import send_massage_user_start
        from models import User

        user = User(tg_id=999, trial=1)
        cache = AsyncMock()
        cache.users.get = AsyncMock(return_value=user)
        manager = _make_manager({"cache": cache})
        message = _make_message(tg_id=999)

        await send_massage_user_start(message, manager)

        manager.start.assert_called_once_with(MainMenu.main, mode=StartMode.RESET_STACK)
