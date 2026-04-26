"""Сервис для работы с тарифными планами.

Предоставляет функции получения списка всех тарифов и поиска по ID
с проверкой существования. Поддерживает фильтрацию для обычных пользователей.
"""

import asyncpg
from fastapi import HTTPException, status
from app.repositories.tariffs import TariffsRepo
from app.core.config import settings

tariffs_repo = TariffsRepo()


async def get_all(conn: asyncpg.Connection, is_admin: bool = False) -> list[dict]:
    if is_admin or not settings.available_rates:
        rows = await tariffs_repo.get_all(conn)
    else:
        rows = await tariffs_repo.get_by_ids(conn, settings.available_rates)
    return [dict(r) for r in rows]


async def get_by_id(conn: asyncpg.Connection, tariff_id: int) -> dict:
    row = await tariffs_repo.get_by_id(conn, tariff_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    return dict(row)
