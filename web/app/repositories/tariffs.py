"""Репозиторий тарифных планов (таблица tariff).

Примечание: таблица называется 'tariff' (ед. число) — согласно схеме БД.
"""

import asyncpg
from typing import Optional

# Таблица называется 'tariff' (не 'tariffs') — из assets/schema.sql бота


class TariffsRepo:
    async def get_all(self, conn: asyncpg.Connection) -> list[asyncpg.Record]:
        return await conn.fetch("SELECT * FROM tariff ORDER BY amount")

    async def get_by_ids(self, conn: asyncpg.Connection, tariff_ids: list[int]) -> list[asyncpg.Record]:
        if not tariff_ids:
            return []
        return await conn.fetch("SELECT * FROM tariff WHERE id = ANY($1) ORDER BY amount", tariff_ids)

    async def get_by_id(self, conn: asyncpg.Connection, tariff_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM tariff WHERE id = $1", tariff_id)
