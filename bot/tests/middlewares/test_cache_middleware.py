from unittest.mock import AsyncMock, MagicMock

import pytest

from middlewares.cache_middleware import CacheMiddleware


class TestCacheMiddleware:
    @pytest.fixture
    def cache_service(self):
        return MagicMock()

    @pytest.fixture
    def middleware(self, cache_service):
        return CacheMiddleware(cache_service=cache_service)

    @pytest.mark.asyncio
    async def test_injects_cache_into_data(self, middleware, cache_service):
        handler = AsyncMock(return_value="ok")
        data = {}

        result = await middleware(handler, MagicMock(), data)

        assert data["cache"] == cache_service
        assert result == "ok"
        handler.assert_called_once()
