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
    async def test_registered_user_from_cache(self, middleware, base_data):
        base_data["cache"].users.get = AsyncMock(return_value=MagicMock())
        handler = AsyncMock()
        event = MagicMock()

        await middleware(handler, event, base_data)

        assert base_data["registration_result"]["type"] == "registered_user"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_event_user_passes_through(self, middleware, base_data):
        base_data["event_from_user"] = None
        handler = AsyncMock()

        await middleware(handler, MagicMock(), base_data)

        handler.assert_called_once()
        assert "registration_result" not in base_data

    @pytest.mark.asyncio
    async def test_check_event_message_with_update(self, middleware):
        """check_event_message returns True when event has message."""
        # Создаём MagicMock, который проходит isinstance проверку
        from aiogram.types import Update
        
        event = MagicMock()
        event.__class__ = Update  # Обманываем isinstance
        event.message = MagicMock()
        event.edited_message = None
        assert middleware.check_event_message(event) is True

    @pytest.mark.asyncio
    async def test_check_event_message_without_message(self, middleware):
        from aiogram.types import Update

        event = MagicMock(spec=Update)
        event.message = None
        event.edited_message = None
        assert not middleware.check_event_message(event)
