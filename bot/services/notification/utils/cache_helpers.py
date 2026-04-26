"""
NotificationDedupeCache — дедупликация уведомлений через PostgreSQL.

Флаги хранятся в таблице `cache` (key = "notif_{funnel_id}_{tg_id}"),
что обеспечивает персистентность между рестартами бота.
Дополнительно кешируем флаги в памяти (L1) для быстрой проверки внутри цикла.
"""

from datetime import datetime, timedelta, timezone

import asyncpg


class NotificationDedupeCache:
    """
    Дедупликация уведомлений с персистентностью через PostgreSQL.

    Использует таблицу `cache` (key TEXT PRIMARY KEY, value JSONB, expires_at TIMESTAMPTZ).
    L1-словарь в памяти ускоряет повторные проверки внутри одного цикла.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._local: dict[str, bool] = {}  # L1: внутрицикловая дедупликация

    def _make_key(self, funnel_id: str, tg_id: int) -> str:
        return f"notif_{funnel_id}_{tg_id}"

    async def is_sent(self, funnel_id: str, tg_id: int) -> bool:
        """Проверить, было ли уже отправлено уведомление данной воронки пользователю."""
        key = self._make_key(funnel_id, tg_id)
        if self._local.get(key):
            return True
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM cache WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                key,
            )
        return row is not None

    async def mark_sent(self, funnel_id: str, tg_id: int, ttl: timedelta) -> None:
        """Зафиксировать, что уведомление отправлено (персистентно, с TTL)."""
        key = self._make_key(funnel_id, tg_id)
        self._local[key] = True
        expires_at = datetime.now(timezone.utc) + ttl
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cache (key, value, expires_at)
                VALUES ($1, '{"sent": true}'::jsonb, $2)
                ON CONFLICT (key) DO UPDATE SET value = '{"sent": true}'::jsonb, expires_at = $2
                """,
                key,
                expires_at,
            )
