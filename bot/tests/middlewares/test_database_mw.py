from unittest.mock import AsyncMock, MagicMock

import pytest

from middlewares.database_mw import DatabaseMiddleware


class TestDatabaseMiddleware:
    @pytest.fixture
    def middleware(self):
        return DatabaseMiddleware()

    @pytest.mark.asyncio
    async def test_injects_session_from_pool(self, middleware):
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_container = MagicMock()
        mock_container.resolve.return_value = mock_pool

        handler = AsyncMock(return_value="ok")
        data = {"container": mock_container}

        result = await middleware(handler, MagicMock(), data)

        assert data["session"] == mock_conn
        assert result == "ok"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_without_container(self, middleware):
        handler = AsyncMock(return_value="fallback")
        data = {}

        result = await middleware(handler, MagicMock(), data)

        assert result == "fallback"
        assert "session" not in data
