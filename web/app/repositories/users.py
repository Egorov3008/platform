"""Репозиторий для работы с таблицей пользователей (users).

Предоставляет CRUD-операции: поиск, получение всех, фильтрация,
подсчёт, управление статусами блокировки и администратора.
"""

import asyncpg
from typing import Optional


class UsersRepo:
    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)

    async def get_all(self, conn: asyncpg.Connection, limit: int = 50, offset: int = 0) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, offset
        )

    async def search(self, conn: asyncpg.Connection, query: str) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM users WHERE username ILIKE $1 OR tg_id::text = $2 LIMIT 50",
            f"%{query}%", query,
        )

    async def count(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval("SELECT COUNT(*) FROM users")

    async def count_today(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE"
        )

    async def set_blocked(self, conn: asyncpg.Connection, tg_id: int, is_blocked: bool) -> None:
        await conn.execute("UPDATE users SET is_blocked = $1 WHERE tg_id = $2", is_blocked, tg_id)

    async def set_admin(self, conn: asyncpg.Connection, tg_id: int, is_admin: bool) -> None:
        await conn.execute("UPDATE users SET is_admin = $1 WHERE tg_id = $2", is_admin, tg_id)

    async def upsert(
        self,
        conn: asyncpg.Connection,
        tg_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
        server_id: int = 2,
        referral_id: Optional[int] = None,
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            """
            INSERT INTO users (tg_id, username, first_name, last_name, language_code, server_id, referral_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (tg_id) DO UPDATE SET
                username = COALESCE($2, users.username),
                first_name = COALESCE($3, users.first_name),
                last_name = COALESCE($4, users.last_name),
                language_code = COALESCE($5, users.language_code),
                server_id = COALESCE($6, users.server_id),
                referral_id = COALESCE($7, users.referral_id)
            RETURNING *
            """,
            tg_id, username, first_name, last_name, language_code, server_id, referral_id,
        )

    async def update_trial(self, conn: asyncpg.Connection, tg_id: int) -> None:
        await conn.execute("UPDATE users SET trial = 1 WHERE tg_id = $1", tg_id)

    async def update_balance(self, conn: asyncpg.Connection, tg_id: int, delta: float) -> None:
        await conn.execute("UPDATE users SET balance = balance + $2 WHERE tg_id = $1", tg_id, delta)
