"""Репозиторий веб-пользователей (таблица web_users).

Хранит учётные записи, созданные через email/password или через
Telegram-авторизацию, с возможностью связывания tg_id.
"""

import asyncpg
from typing import Optional


class WebUsersRepo:
    async def create(
        self, conn: asyncpg.Connection, email: str, password_hash: str, tg_id: Optional[int]
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            "INSERT INTO web_users (email, password_hash, tg_id) VALUES ($1, $2, $3) RETURNING *",
            email, password_hash, tg_id,
        )

    async def get_by_email(self, conn: asyncpg.Connection, email: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM web_users WHERE email = $1", email)

    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM web_users WHERE tg_id = $1", tg_id)

    async def link_tg_id(self, conn: asyncpg.Connection, user_id: int, tg_id: int) -> None:
        await conn.execute("UPDATE web_users SET tg_id = $1 WHERE id = $2", tg_id, user_id)
