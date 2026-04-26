"""Репозиторий одноразовых magic-токенов для входа через Telegram.

Управляет созданием токенов с TTL, проверкой валидности и отметкой
об использовании.
"""

import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional


class MagicTokensRepo:
    async def create(self, conn: asyncpg.Connection, tg_id: int, ttl_minutes: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        row = await conn.fetchrow(
            "INSERT INTO magic_tokens (tg_id, expires_at) VALUES ($1, $2) RETURNING token::text",
            tg_id, expires_at,
        )
        return row["token"]

    async def consume(self, conn: asyncpg.Connection, token: str) -> Optional[asyncpg.Record]:
        """Атомарно проверяет и помечает токен использованным. Защита от TOCTOU."""
        return await conn.fetchrow(
            """
            UPDATE magic_tokens
            SET used = TRUE
            WHERE token = $1::uuid
              AND used = FALSE
              AND expires_at > NOW()
            RETURNING *
            """,
            token,
        )
