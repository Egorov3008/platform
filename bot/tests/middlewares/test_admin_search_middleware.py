from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Update

from middlewares.admin_search_middleware import AdminSearchMiddleware


ADMIN_IDS = [100, 200]


@pytest.fixture(autouse=True)
def patch_admin_ids(monkeypatch):
    """Подменяем ADMIN_ID константу в модуле middleware."""
    monkeypatch.setattr(
        "middlewares.admin_search_middleware.ADMIN_ID", ADMIN_IDS
    )


def _make_update(text: str | None = None) -> Update:
    """Создаёт MagicMock, который проходит isinstance(event, Update)."""
    event = MagicMock()
    event.__class__ = Update
    if text is not None:
        event.message = MagicMock()
        event.message.text = text
        event.edited_message = None
    else:
        event.message = None
        event.edited_message = None
    return event


def _make_data(user_id: int) -> dict:
    return {"event_from_user": MagicMock(id=user_id)}


class TestAdminSearchMiddleware:
    @pytest.fixture
    def middleware(self):
        return AdminSearchMiddleware()

    # ------------------------------------------------------------------
    # _is_admin
    # ------------------------------------------------------------------

    def test_is_admin_returns_true_for_known_admin(self, middleware):
        assert middleware._is_admin(100) is True

    def test_is_admin_returns_false_for_regular_user(self, middleware):
        assert middleware._is_admin(999) is False

    # ------------------------------------------------------------------
    # _extract_search_tg_id
    # ------------------------------------------------------------------

    def test_extract_valid_token(self, middleware):
        event = _make_update("/start search_12345")
        result = middleware._extract_search_tg_id(event)
        assert result == 12345

    def test_extract_returns_none_for_non_update(self, middleware):
        result = middleware._extract_search_tg_id(MagicMock())
        assert result is None

    def test_extract_returns_none_for_start_without_param(self, middleware):
        event = _make_update("/start")
        result = middleware._extract_search_tg_id(event)
        assert result is None

    def test_extract_returns_none_for_different_prefix(self, middleware):
        event = _make_update("/start ref_12345")
        result = middleware._extract_search_tg_id(event)
        assert result is None

    def test_extract_returns_none_for_non_numeric_id(self, middleware):
        event = _make_update("/start search_abc")
        result = middleware._extract_search_tg_id(event)
        assert result is None

    def test_extract_returns_none_for_empty_id(self, middleware):
        event = _make_update("/start search_")
        result = middleware._extract_search_tg_id(event)
        assert result is None

    def test_extract_returns_none_for_non_start_command(self, middleware):
        event = _make_update("/help search_12345")
        result = middleware._extract_search_tg_id(event)
        assert result is None

    def test_extract_returns_none_when_no_message(self, middleware):
        event = _make_update()
        result = middleware._extract_search_tg_id(event)
        assert result is None

    # ------------------------------------------------------------------
    # __call__ — основная логика
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_admin_search_token_sets_data(self, middleware):
        """Администратор с корректным токеном получает admin_search_tg_id в data."""
        handler = AsyncMock()
        event = _make_update("/start search_99999")
        data = _make_data(user_id=100)  # 100 — в ADMIN_IDS

        await middleware(handler, event, data)

        assert data.get("admin_search_tg_id") == 99999
        handler.assert_called_once_with(event, data)

    @pytest.mark.asyncio
    async def test_non_admin_search_token_ignored(self, middleware):
        """Обычный пользователь с searce_ токеном не получает admin_search_tg_id."""
        handler = AsyncMock()
        event = _make_update("/start search_99999")
        data = _make_data(user_id=777)  # не в ADMIN_IDS

        await middleware(handler, event, data)

        assert "admin_search_tg_id" not in data
        handler.assert_called_once_with(event, data)

    @pytest.mark.asyncio
    async def test_admin_regular_start_not_affected(self, middleware):
        """Обычный /start от администратора не устанавливает admin_search_tg_id."""
        handler = AsyncMock()
        event = _make_update("/start")
        data = _make_data(user_id=100)

        await middleware(handler, event, data)

        assert "admin_search_tg_id" not in data
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_event_user_passes_through(self, middleware):
        """Если event_from_user не установлен, middleware не вмешивается."""
        handler = AsyncMock()
        event = _make_update("/start search_12345")
        data = {"event_from_user": None}

        await middleware(handler, event, data)

        assert "admin_search_tg_id" not in data
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_with_gift_token_not_affected(self, middleware):
        """Токен подарка у администратора не создаёт admin_search_tg_id."""
        handler = AsyncMock()
        event = _make_update("/start gift_abc123")
        data = _make_data(user_id=100)

        await middleware(handler, event, data)

        assert "admin_search_tg_id" not in data

    @pytest.mark.asyncio
    async def test_handler_always_called(self, middleware):
        """Хендлер вызывается в любом случае."""
        handler = AsyncMock()
        event = _make_update(None)
        data = {"event_from_user": None}

        await middleware(handler, event, data)

        handler.assert_called_once_with(event, data)
