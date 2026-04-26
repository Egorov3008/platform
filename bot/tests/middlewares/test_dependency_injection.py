from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middlewares.dependency_injection import DependencyInjectionMiddleware


class TestDependencyInjectionMiddleware:
    @pytest.fixture(autouse=True)
    def reset_container(self):
        original = DependencyInjectionMiddleware.container
        DependencyInjectionMiddleware.container = MagicMock()
        yield
        DependencyInjectionMiddleware.container = original

    @pytest.fixture
    def middleware(self):
        return DependencyInjectionMiddleware()

    @pytest.mark.asyncio
    async def test_injects_container_into_data(self, middleware):
        handler = AsyncMock()
        event = MagicMock()
        data = {}

        await middleware(handler, event, data)

        assert "container" in data
        assert data["container"] == DependencyInjectionMiddleware.container
        handler.assert_called_once_with(event, data)

    @pytest.mark.asyncio
    async def test_calls_handler_and_returns_result(self, middleware):
        handler = AsyncMock(return_value="result")
        event = MagicMock()
        data = {}

        result = await middleware(handler, event, data)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_initializes_container_when_none(self):
        DependencyInjectionMiddleware.container = None
        middleware = DependencyInjectionMiddleware()
        handler = AsyncMock()
        mock_container = MagicMock()

        with patch(
            "middlewares.dependency_injection.get_container",
            new_callable=AsyncMock,
            return_value=mock_container,
        ):
            await middleware(handler, MagicMock(), {})

        assert DependencyInjectionMiddleware.container == mock_container
