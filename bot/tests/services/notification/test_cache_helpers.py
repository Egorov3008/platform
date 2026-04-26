"""
Тесты для NotificationDedupeCache (services/notification/utils/cache_helpers.py).

NotificationDedupeCache теперь использует asyncpg.Pool для персистентной дедупликации
через таблицу `cache` в PostgreSQL (выживает рестарты бота).
"""

import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from services.notification.utils.cache_helpers import NotificationDedupeCache


_FUNNEL_ID = "key_expiry_24h"
_TG_ID = 123456


@pytest.fixture
def mock_pool():
    """Mock asyncpg.Pool для тестирования."""
    pool = MagicMock()
    pool.acquire = MagicMock()
    return pool


@pytest.fixture
def mock_conn():
    """Mock asyncpg connection."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
async def dedupe(mock_pool, mock_conn):
    """Fixture для NotificationDedupeCache с мокированным pool."""
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None
    return NotificationDedupeCache(mock_pool)


class TestNotificationDedupeCache:
    """Тесты для NotificationDedupeCache (DB-backed)."""

    async def test_is_sent_returns_false_when_not_in_db(self, dedupe, mock_conn):
        """Если записи нет в БД, is_sent возвращает False."""
        mock_conn.fetchrow.return_value = None
        result = await dedupe.is_sent(_FUNNEL_ID, _TG_ID)
        assert result is False

    async def test_is_sent_returns_true_when_in_db(self, dedupe, mock_conn):
        """Если запись есть в БД и не истекла, is_sent возвращает True."""
        mock_conn.fetchrow.return_value = {"1": 1}  # Имитация хотя бы одной строки
        result = await dedupe.is_sent(_FUNNEL_ID, _TG_ID)
        assert result is True

    async def test_is_sent_uses_local_cache(self, dedupe, mock_conn):
        """L1-кеш в памяти срабатывает без БД-запроса (внутри цикла)."""
        # Первый вызов mark_sent заполняет L1-кеш
        ttl = timedelta(hours=25)
        await dedupe.mark_sent(_FUNNEL_ID, _TG_ID, ttl)
        # Сбрасываем mock чтобы отследить второй вызов
        mock_conn.fetchrow.reset_mock()
        # Второй вызов is_sent должен вернуть True из L1 без DB-запроса
        result = await dedupe.is_sent(_FUNNEL_ID, _TG_ID)
        assert result is True
        mock_conn.fetchrow.assert_not_called()

    async def test_mark_sent_inserts_to_db(self, dedupe, mock_conn):
        """mark_sent сохраняет запись в таблицу `cache` с TTL."""
        ttl = timedelta(hours=25)
        await dedupe.mark_sent(_FUNNEL_ID, _TG_ID, ttl)
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO cache" in call_args[0][0]
        assert f"notif_{_FUNNEL_ID}_{_TG_ID}" in call_args[0]

    async def test_is_sent_queries_db_with_expiry_check(self, dedupe, mock_conn):
        """is_sent проверяет только невыполненные записи (expires_at > NOW())."""
        mock_conn.fetchrow.return_value = None
        await dedupe.is_sent(_FUNNEL_ID, _TG_ID)
        call_args = mock_conn.fetchrow.call_args
        assert "expires_at > NOW()" in call_args[0][0] or "expires_at IS NULL" in call_args[0][0]

    def test_make_key_format(self, dedupe):
        """Ключ сохраняет формат notif_{funnel_id}_{tg_id}."""
        key = dedupe._make_key("trial_unused", 999)
        assert key == "notif_trial_unused_999"

    async def test_different_funnel_ids_use_different_keys(self, dedupe, mock_conn):
        """Разные воронки используют разные ключи."""
        mock_conn.fetchrow.return_value = None
        await dedupe.is_sent("funnel_a", _TG_ID)
        await dedupe.is_sent("funnel_b", _TG_ID)
        calls = mock_conn.fetchrow.call_args_list
        key_a = calls[0][0][1]
        key_b = calls[1][0][1]
        assert "funnel_a" in key_a
        assert "funnel_b" in key_b
        assert key_a != key_b

    async def test_different_tg_ids_use_different_keys(self, dedupe, mock_conn):
        """Разные пользователи используют разные ключи."""
        mock_conn.fetchrow.return_value = None
        await dedupe.is_sent(_FUNNEL_ID, 111)
        await dedupe.is_sent(_FUNNEL_ID, 222)
        calls = mock_conn.fetchrow.call_args_list
        key_111 = calls[0][0][1]
        key_222 = calls[1][0][1]
        assert "111" in key_111
        assert "222" in key_222
        assert key_111 != key_222
