from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram_dialog.api.exceptions import UnknownIntent

from middlewares.dialog_error_handler import DialogExceptionHandlerMiddleware


class TestDialogExceptionHandlerMiddleware:
    @pytest.fixture
    def middleware(self):
        return DialogExceptionHandlerMiddleware()

    @pytest.mark.asyncio
    async def test_passes_through_on_success(self, middleware):
        handler = AsyncMock(return_value="ok")
        result = await middleware(handler, MagicMock(), {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_handles_unknown_intent(self, middleware):
        handler = AsyncMock(side_effect=UnknownIntent("test"))
        mock_bot = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 123
        data = {"bot": mock_bot, "event_from_user": mock_user}

        result = await middleware(handler, MagicMock(), data)

        assert result is None
        mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_reraises_other_exceptions(self, middleware):
        handler = AsyncMock(side_effect=ValueError("unexpected"))

        with pytest.raises(ValueError, match="unexpected"):
            await middleware(handler, MagicMock(), {})
