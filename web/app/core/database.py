"""Модуль управления пулом подключений к PostgreSQL.

Обеспечивает создание, закрытие и доступ к пулу asyncpg в рамках
жизненного цикла FastAPI-приложения.
"""

import asyncpg
from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool
