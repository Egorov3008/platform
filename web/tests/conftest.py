import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_conn():
    """Создаёт mock-соединение asyncpg с методами, работающими как async."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value="")

    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_conn, mock_pool


@pytest.fixture(autouse=True)
def disable_csrf(monkeypatch):
    """Отключает CSRF middleware в тестах."""
    from app.core import config
    monkeypatch.setattr(config.settings, "csrf_enabled", False)
