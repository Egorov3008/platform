"""Репозиторий для работы с таблицей stocks (персональные скидки пользователей)."""

import asyncpg
from typing import Optional


class StocksRepo:
    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        """Получить скидку пользователя, если она активна и не истекла."""
        return await conn.fetchrow(
            """
            SELECT * FROM stocks
            WHERE tg_id = $1 AND is_active = true
            AND (valid_until IS NULL OR valid_until > NOW())
            LIMIT 1
            """,
            tg_id,
        )

    async def create(
        self,
        conn: asyncpg.Connection,
        tg_id: int,
        stock_type: str,
        value: float,
        valid_until: Optional[str] = None,
    ) -> asyncpg.Record:
        """Создать новую скидку для пользователя."""
        return await conn.fetchrow(
            """
            INSERT INTO stocks (tg_id, stock_type, value, is_active, valid_until)
            VALUES ($1, $2, $3, true, $4)
            ON CONFLICT (tg_id) DO UPDATE SET
                stock_type = $2,
                value = $3,
                valid_until = $4,
                is_active = true
            RETURNING *
            """,
            tg_id, stock_type, value, valid_until,
        )

    async def deactivate(self, conn: asyncpg.Connection, tg_id: int) -> None:
        """Отключить скидку пользователя."""
        await conn.execute("UPDATE stocks SET is_active = false WHERE tg_id = $1", tg_id)
