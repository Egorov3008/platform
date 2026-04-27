"""Сервис бизнес-логики для административных операций.

NOTE: Admin operations have been moved to backend API.
This module is deprecated and kept temporarily for reference.
User management is now handled by backend /api/v1/admin/ endpoints.
"""

import asyncpg
from fastapi import HTTPException, status
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_users(conn: asyncpg.Connection, limit: int, offset: int, search: str | None) -> list[dict]:
    """Deprecated - use backend API instead."""
    raise NotImplementedError("User listing has been moved to backend API. Use /api/v1/admin/users")


async def get_user(conn: asyncpg.Connection, tg_id: int) -> dict:
    """Deprecated - use backend API instead."""
    raise NotImplementedError("User lookup has been moved to backend API. Use /api/v1/admin/users/{tg_id}")


async def patch_user(conn: asyncpg.Connection, tg_id: int, is_blocked: bool | None, is_admin: bool | None) -> dict:
    """Deprecated - use backend API instead."""
    raise NotImplementedError("User update has been moved to backend API. Use PATCH /api/v1/admin/users/{tg_id}")
