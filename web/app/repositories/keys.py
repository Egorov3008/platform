"""Репозиторий для работы с таблицей ключей (keys).

Обеспечивает хранение, поиск по tg_id и client_id, подсчёт активных/
истекающих ключей и обновление срока действия.
"""

import asyncpg
from typing import Optional


class KeysRepo:
    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM keys WHERE tg_id = $1 ORDER BY created_at DESC", tg_id
        )

    async def get_by_client_id(self, conn: asyncpg.Connection, client_id: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM keys WHERE client_id = $1", client_id)

    async def get_by_email(self, conn: asyncpg.Connection, email: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM keys WHERE email = $1", email)

    async def get_all(self, conn: asyncpg.Connection, limit: int = 50, offset: int = 0) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT k.*, u.username FROM keys k LEFT JOIN users u ON k.tg_id = u.tg_id "
            "ORDER BY k.created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )

    async def count_active(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM keys WHERE expiry_time > EXTRACT(EPOCH FROM NOW()) * 1000"
        )

    async def count_expiring_soon(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM keys WHERE expiry_time > EXTRACT(EPOCH FROM NOW()) * 1000 "
            "AND expiry_time < EXTRACT(EPOCH FROM (NOW() + INTERVAL '24 hours')) * 1000"
        )

    async def store(
        self, conn: asyncpg.Connection, tg_id: int, client_id: str, email: str,
        expiry_time: int, key: str, inbound_id: int, tariff_id: int,
        total_gb: float = 0.0, reset_date: int = 0
    ) -> asyncpg.Record:
        import time
        created_at = int(time.time() * 1000)
        return await conn.fetchrow(
            """
            INSERT INTO keys
                (tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
            """,
            tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date, created_at,
        )

    async def delete(self, conn: asyncpg.Connection, client_id: str) -> None:
        await conn.execute("DELETE FROM keys WHERE client_id = $1", client_id)

    async def update_expiry(
        self, conn: asyncpg.Connection, client_id: str,
        new_expiry_time: int, tariff_id: int, total_gb: float
    ) -> None:
        await conn.execute(
            "UPDATE keys SET expiry_time = $2, tariff_id = $3, total_gb = $4, "
            "notified_10h = FALSE, notified_24h = FALSE WHERE client_id = $1",
            client_id, new_expiry_time, tariff_id, total_gb,
        )
