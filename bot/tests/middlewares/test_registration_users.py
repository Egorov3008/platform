from unittest.mock import AsyncMock, MagicMock

import pytest

from middlewares.registration_users import RegistrationUsersMiddleware


class TestRegistrationUsersMiddleware:
    @pytest.fixture
    def middleware(self):
        return RegistrationUsersMiddleware()

    @pytest.fixture
    def base_data(self):
        mock_cache = AsyncMock()
        mock_cache.users.get = AsyncMock(return_value=None)
        container = MagicMock()
        return {
            "container": container,
            "cache": mock_cache,
            "event_from_user": MagicMock(id=123),
        }

    @pytest.mark.asyncio
    async def test_registered_user_from_backend_when_event_is_not_update(self, middleware, base_data):
        """Если backend подтвердил регистрацию — middleware помечает
        registration_result='registered_user' и сразу вызывает handler
        (даже если event не является Update — это вспомогательный путь)."""
        from api.backend_client import BackendAPIClient
        from api.schemas import UserDTO

        backend_user = UserDTO(tg_id=123, username="test", first_name="Test", balance=0.0, trial=0, server_id=1, is_admin=False, is_blocked=False)
        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=backend_user)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        handler = AsyncMock()
        event = MagicMock()

        await middleware(handler, event, base_data)

        assert base_data["registration_result"]["type"] == "registered_user"
        assert base_data["registration_result"]["trial"] == 0
        mock_backend.get_user.assert_awaited_once_with(123)
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_event_user_passes_through(self, middleware, base_data):
        base_data["event_from_user"] = None
        handler = AsyncMock()

        await middleware(handler, MagicMock(), base_data)

        handler.assert_awaited_once()
        assert "registration_result" not in base_data

    @pytest.mark.asyncio
    async def test_check_event_message_with_update(self, middleware):
        """check_event_message returns True when event has message."""
        # Use a real aiogram Update so isinstance(event, Update) passes.
        from aiogram.types import Update, Message
        from unittest.mock import MagicMock

        # Build a real Update with a non-None message
        update = Update(update_id=1, message=MagicMock(spec=Message))
        assert middleware.check_event_message(update) is True

    @pytest.mark.asyncio
    async def test_registered_user_from_backend(self, middleware, base_data):
        from api.backend_client import BackendAPIClient
        from api.schemas import UserDTO

        backend_user = UserDTO(
            tg_id=123, username="u", first_name="F",
            balance=0.0, trial=0, server_id=1,
            is_admin=False, is_blocked=False,
        )
        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=backend_user)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        handler = AsyncMock()
        await middleware(handler, MagicMock(), base_data)

        assert base_data["registration_result"]["type"] == "registered_user"
        mock_backend.get_user.assert_awaited_once_with(123)
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unregistered_user_no_token_marks_unknown(self, middleware, base_data):
        """Если backend не нашёл пользователя и это не Update с /start — токен
        не извлекается, registration_result='unknown_user' (для auto_register)."""
        from api.backend_client import BackendAPIClient

        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=None)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        from aiogram.types import Update
        event = MagicMock()
        event.__class__ = Update
        event.message = None
        event.edited_message = None

        handler = AsyncMock()
        await middleware(handler, event, base_data)

        handler.assert_awaited_once()
        assert base_data["registration_result"]["type"] == "unknown_user"
        assert base_data["registration_result"]["success"] is False

    @pytest.mark.asyncio
    async def test_unregistered_user_with_start_no_token_marks_unknown(self, middleware, base_data):
        """/start без токена → registration_result='unknown_user'."""
        from api.backend_client import BackendAPIClient

        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=None)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        from aiogram.types import Update
        event = MagicMock()
        event.__class__ = Update
        msg = MagicMock()
        msg.text = "/start"
        event.message = msg
        event.edited_message = None

        handler = AsyncMock()
        await middleware(handler, event, base_data)

        handler.assert_awaited_once()
        assert base_data["registration_result"]["type"] == "unknown_user"

    @pytest.mark.asyncio
    async def test_check_event_message_without_message(self, middleware):
        from aiogram.types import Update

        event = MagicMock(spec=Update)
        event.message = None
        event.edited_message = None
        assert not middleware.check_event_message(event)

    @pytest.mark.asyncio
    async def test_existing_user_with_landing_token(self, middleware, base_data):
        """Существующий юзер пришёл по /start landing_<uid> → type='landing',
        is_registered=True (handler вызовет mark-converted)."""
        from api.backend_client import BackendAPIClient
        from api.schemas import UserDTO

        backend_user = UserDTO(
            tg_id=123, username="u", first_name="F",
            balance=0.0, trial=1, server_id=1,
            is_admin=False, is_blocked=False,
        )
        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=backend_user)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        from aiogram.types import Update
        event = MagicMock()
        event.__class__ = Update
        msg = MagicMock()
        msg.text = "/start landing_abc123def456"
        event.message = msg
        event.edited_message = None

        handler = AsyncMock()
        await middleware(handler, event, base_data)

        rr = base_data["registration_result"]
        assert rr["type"] == "landing"
        assert rr["is_registered"] is True
        assert rr["landing_uid"] == "abc123def456"
        assert rr["trial"] == 1
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_existing_user_plain_start_still_registered_user(self, middleware, base_data):
        """Существующий юзер с /start без landing-токена → обычный registered_user
        (регрессия: landing-ветка не должна перехватывать обычные /start)."""
        from api.backend_client import BackendAPIClient
        from api.schemas import UserDTO

        backend_user = UserDTO(
            tg_id=123, username="u", first_name="F",
            balance=0.0, trial=0, server_id=1,
            is_admin=False, is_blocked=False,
        )
        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=backend_user)
        base_data["container"].resolve = MagicMock(return_value=mock_backend)

        from aiogram.types import Update
        event = MagicMock()
        event.__class__ = Update
        msg = MagicMock()
        msg.text = "/start"
        event.message = msg
        event.edited_message = None

        handler = AsyncMock()
        await middleware(handler, event, base_data)

        assert base_data["registration_result"]["type"] == "registered_user"

    @pytest.mark.asyncio
    async def test_new_user_with_landing_token(self, middleware, base_data):
        """Новый юзер с /start landing_<uid> → factory возвращает type='landing',
        is_registered=False (handler вызовет авто-регистрацию + claim)."""
        from api.backend_client import BackendAPIClient
        from registration.registration_factory import RegistrationFactory
        from registration.landing_registration import LandingRegistration
        from registration.gift_registration import GiftRegistration
        from registration.referral_registration import ReferralRegistration

        mock_backend = AsyncMock(spec=BackendAPIClient)
        mock_backend.get_user = AsyncMock(return_value=None)

        factory = MagicMock()
        factory.register_handler = MagicMock()
        factory.handle_registration = AsyncMock(
            return_value={
                "success": True,
                "type": "landing",
                "landing_uid": "abc123def456",
                "is_registered": False,
            }
        )

        def resolve(cls):
            if cls is RegistrationFactory:
                return factory
            if cls is LandingRegistration:
                return LandingRegistration()
            if cls is GiftRegistration:
                return MagicMock()
            if cls is ReferralRegistration:
                return MagicMock()
            if cls is BackendAPIClient:
                return mock_backend
            raise AssertionError(f"unexpected resolve: {cls}")

        base_data["container"].resolve = MagicMock(side_effect=resolve)

        from aiogram.types import Update
        event = MagicMock()
        event.__class__ = Update
        msg = MagicMock()
        msg.text = "/start landing_abc123def456"
        event.message = msg
        event.edited_message = None

        handler = AsyncMock()
        await middleware(handler, event, base_data)

        rr = base_data["registration_result"]
        assert rr["type"] == "landing"
        assert rr["landing_uid"] == "abc123def456"
        assert rr["is_registered"] is False
        handler.assert_awaited_once()
