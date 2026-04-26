"""Сервис бизнес-логики для административных операций.

Содержит функции получения списка пользователей с подсчётом ключей,
просмотра/обновления профиля пользователя и принудительного удаления
ключей (с синхронизацией с 3x-UI).
"""

import asyncpg
from fastapi import HTTPException, status
from app.repositories.users import UsersRepo
from app.repositories.keys import KeysRepo
from app.core.logging import get_logger

logger = get_logger(__name__)

users_repo = UsersRepo()
keys_repo = KeysRepo()


async def get_users(conn: asyncpg.Connection, limit: int, offset: int, search: str | None) -> list[dict]:
    logger.debug("Получение списка пользователей: limit=%d, offset=%d, search=%s", limit, offset, search)
    rows = await (users_repo.search(conn, search) if search else users_repo.get_all(conn, limit, offset))
    result = []
    for row in rows:
        keys = await keys_repo.get_by_tg_id(conn, row["tg_id"])
        result.append({**dict(row), "keys_count": len(keys)})
    return result


async def get_user(conn: asyncpg.Connection, tg_id: int) -> dict:
    user = await users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        logger.warning("Пользователь не найден: tg_id=%d", tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    keys = await keys_repo.get_by_tg_id(conn, tg_id)
    logger.debug("Получение информации о пользователе: tg_id=%d", tg_id)
    return {**dict(user), "keys": [dict(k) for k in keys]}


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


async def get_all_keys(conn: asyncpg.Connection, limit: int, offset: int) -> list[dict]:
    logger.debug("Получение списка всех ключей: limit=%d, offset=%d", limit, offset)
    return [dict(r) for r in await keys_repo.get_all(conn, limit, offset)]


async def admin_force_delete_key(conn: asyncpg.Connection, client_id: str) -> None:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row:
        logger.warning("Ключ не найден для административного удаления: client_id=%s", client_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    logger.info("Административное удаление ключа: client_id=%s", client_id)
    from app.core.xui import get_xui_client
    api = await get_xui_client()
    from app.services.keys import _xui_delete_client
    try:
        await _xui_delete_client(api, client_id)
        logger.info("Клиент удалён из 3x-UI: client_id=%s", client_id)
    except Exception as e:
        logger.error("Ошибка при удалении клиента из 3x-UI: %s", str(e))
        raise
    await keys_repo.delete(conn, client_id)
    logger.info("Ключ успешно удалён из БД: client_id=%s", client_id)
