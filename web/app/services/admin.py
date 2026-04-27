"""Сервис бизнес-логики для административных операций.

Содержит функции получения списка пользователей, просмотра/обновления
профиля пользователя. Операции с ключами делегируются backend API.
"""

import asyncpg
from fastapi import HTTPException, status
from app.repositories.users import UsersRepo
from app.core.logging import get_logger

logger = get_logger(__name__)

users_repo = UsersRepo()


async def get_users(conn: asyncpg.Connection, limit: int, offset: int, search: str | None) -> list[dict]:
    logger.debug("Получение списка пользователей: limit=%d, offset=%d, search=%s", limit, offset, search)
    rows = await (users_repo.search(conn, search) if search else users_repo.get_all(conn, limit, offset))
    # Note: keys_count would require backend API call; for now return users without count
    # This can be enhanced in future by calling backend.list_keys(tg_id)
    result = []
    for row in rows:
        result.append(dict(row))
    return result


async def get_user(conn: asyncpg.Connection, tg_id: int) -> dict:
    user = await users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        logger.warning("Пользователь не найден: tg_id=%d", tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.debug("Получение информации о пользователе: tg_id=%d", tg_id)
    # Note: keys would require backend API call; for now return user without keys
    return dict(user)


async def patch_user(conn: asyncpg.Connection, tg_id: int, is_blocked: bool | None, is_admin: bool | None) -> dict:
    if not await users_repo.get_by_tg_id(conn, tg_id):
        logger.warning("Пользователь не найден для обновления: tg_id=%d", tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if is_blocked is not None:
        await users_repo.set_blocked(conn, tg_id, is_blocked)
        logger.info("Обновлено поле is_blocked=%s для tg_id=%d", is_blocked, tg_id)
    if is_admin is not None:
        await users_repo.set_admin(conn, tg_id, is_admin)
        logger.info("Обновлено поле is_admin=%s для tg_id=%d", is_admin, tg_id)
    return dict(await users_repo.get_by_tg_id(conn, tg_id))
