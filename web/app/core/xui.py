"""Модуль клиента для панели управления 3x-UI.

Обеспечивает управление AsyncApi клиентами для каждого сервера 3x-UI,
привязанного к пользователю через server_id.
"""

import asyncpg
from py3xui import AsyncApi
from app.core.logging import get_logger

logger = get_logger(__name__)

_xui_clients: dict[int, AsyncApi] = {}


async def get_server_by_tg_id(conn: asyncpg.Connection, tg_id: int) -> dict | None:
    """Получает информацию о сервере пользователя из БД."""
    row = await conn.fetchrow(
        """
        SELECT s.id, s.api_url, s.login, s.password
        FROM servers s
        JOIN users u ON u.server_id = s.id
        WHERE u.tg_id = $1
        """,
        tg_id
    )
    return dict(row) if row else None


async def get_xui_client(conn: asyncpg.Connection, tg_id: int) -> AsyncApi:
    """Возвращает авторизованный клиент py3xui для сервера пользователя."""
    server = await get_server_by_tg_id(conn, tg_id)
    if not server:
        raise ValueError(f"Server not found for user {tg_id}")

    server_id = server["id"]

    if server_id not in _xui_clients:
        logger.debug(f"Creating XUI client for server {server_id} (user {tg_id})")
        client = AsyncApi(
            host=server["api_url"],
            username=server["login"],
            password=server["password"],
        )
        try:
            await client.login()
            _xui_clients[server_id] = client
            logger.info(f"XUI client created and logged in for server {server_id}")
        except Exception as e:
            logger.error(f"Failed to login to XUI server {server_id}: {str(e)}")
            raise

    return _xui_clients[server_id]


async def reset_xui_client(server_id: int) -> None:
    """Сбрасывает кэшированный клиент для сервера."""
    if server_id in _xui_clients:
        logger.debug(f"Resetting XUI client for server {server_id}")
        del _xui_clients[server_id]


async def xui_call(conn: asyncpg.Connection, tg_id: int, coro_factory):
    """Выполняет вызов 3x-UI с автоматическим повтором при истечении сессии."""
    server = await get_server_by_tg_id(conn, tg_id)
    if not server:
        raise ValueError(f"Server not found for user {tg_id}")

    server_id = server["id"]

    try:
        return await coro_factory(await get_xui_client(conn, tg_id))
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("401", "403", "unauthorized", "forbidden", "auth", "login")):
            logger.debug(f"Auth error for server {server_id}, resetting client: {str(e)}")
            await reset_xui_client(server_id)
            return await coro_factory(await get_xui_client(conn, tg_id))
        raise
