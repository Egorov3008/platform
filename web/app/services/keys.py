"""Сервис управления VPN-ключами: создание, продление, удаление.

Координирует работу с 3x-UI (добавление/удаление/обновление клиентов)
и сохранение информации о ключах в базе данных.
"""

import uuid
import asyncpg
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.repositories.keys import KeysRepo
from app.repositories.tariffs import TariffsRepo
from app.repositories.users import UsersRepo
from app.core.config import settings
from app.core.xui import xui_call
from app.core.logging import get_logger

logger = get_logger(__name__)

keys_repo = KeysRepo()
tariffs_repo = TariffsRepo()
users_repo = UsersRepo()


def _expiry_ms(period_days: int) -> int:
    """Вычисляет время истечения ключа в миллисекундах (epoch)."""
    expiry_dt = datetime.now(timezone.utc) + timedelta(days=period_days)
    return int(expiry_dt.timestamp() * 1000)


def _random_email() -> str:
    """Генерирует уникальный email-идентификатор ключа."""
    return f"web_{uuid.uuid4().hex[:12]}"


async def _xui_add_client(
    api, client_id: str, email: str,
    expiry_ms: int, total_gb: int, limit_ip: int,
) -> None:
    """Добавляет клиента в 3x-UI."""
    from py3xui import Client
    client = Client(
        id=client_id,
        email=email,
        expiry_time=expiry_ms,
        total_gb=total_gb,
        limit_ip=limit_ip,
        enable=True,
    )
    await api.client.add(inbound_id=settings.xui_inbound_id, clients=[client])


async def _xui_delete_client(api, client_id: str) -> None:
    await api.client.delete(inbound_id=settings.xui_inbound_id, client_uuid=client_id)


async def _xui_update_client(
    api, client_id: str, email: str,
    expiry_ms: int, total_gb: int, limit_ip: int,
) -> None:
    from py3xui import Client
    client = Client(
        id=client_id,
        email=email,
        expiry_time=expiry_ms,
        total_gb=total_gb,
        limit_ip=limit_ip,
        enable=True,
    )
    await api.client.update(client_uuid=client_id, client=client)


async def get_user_keys(conn: asyncpg.Connection, tg_id: int) -> list[dict]:
    logger.debug("Получение ключей для tg_id=%d", tg_id)
    return [dict(r) for r in await keys_repo.get_by_tg_id(conn, tg_id)]


async def create_key(conn: asyncpg.Connection, tg_id: int, tariff_id: int) -> dict:
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        logger.error("Тариф не найден: tariff_id=%d", tariff_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    client_id = str(uuid.uuid4())
    email = _random_email()
    expiry = _expiry_ms(tariff["period"])
    total_gb = int(tariff["traffic_limit"] * (2 ** 30)) if tariff["traffic_limit"] > 0 else 0

    logger.info(
        "Создание ключа: tg_id=%d, tariff_id=%d, client_id=%s, email=%s",
        tg_id, tariff_id, client_id, email
    )

    try:
        await xui_call(conn, tg_id, lambda api: _xui_add_client(api, client_id, email, expiry, total_gb, tariff["limit_ip"]))
        logger.info("Клиент добавлен в 3x-UI: client_id=%s", client_id)
    except Exception as e:
        logger.error("Ошибка при добавлении клиента в 3x-UI: %s", str(e))
        raise

    sub_base = settings.xui_subscription_url or settings.xui_api_url
    subscription_url = f"{sub_base}/sub/{email}"
    row = await keys_repo.store(
        conn, tg_id=tg_id, client_id=client_id, email=email,
        expiry_time=expiry, key=subscription_url,
        inbound_id=settings.xui_inbound_id, tariff_id=tariff_id,
        total_gb=float(total_gb),
    )
    logger.info("Ключ успешно создан: client_id=%s для tg_id=%d", client_id, tg_id)
    return dict(row)


async def delete_key(conn: asyncpg.Connection, client_id: str, tg_id: int) -> None:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row or row["tg_id"] != tg_id:
        logger.warning("Ключ не найден для удаления: client_id=%s, tg_id=%d", client_id, tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    logger.info("Удаление ключа: client_id=%s, tg_id=%d", client_id, tg_id)
    try:
        await xui_call(conn, tg_id, lambda api: _xui_delete_client(api, client_id))
        logger.info("Клиент удалён из 3x-UI: client_id=%s", client_id)
    except Exception as e:
        logger.error("Ошибка при удалении клиента из 3x-UI: %s", str(e))
        raise
    await keys_repo.delete(conn, client_id)
    logger.info("Ключ успешно удалён из БД: client_id=%s", client_id)


async def renew_key(conn: asyncpg.Connection, client_id: str, tg_id: int, tariff_id: int) -> dict:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row or row["tg_id"] != tg_id:
        logger.warning("Ключ не найден для продления: client_id=%s, tg_id=%d", client_id, tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        logger.error("Тариф не найден: tariff_id=%d", tariff_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    new_expiry = _expiry_ms(tariff["period"])
    total_gb = int(tariff["traffic_limit"] * (2 ** 30)) if tariff["traffic_limit"] > 0 else 0

    logger.info(
        "Продление ключа: client_id=%s, tg_id=%d, tariff_id=%d, новый срок=%d",
        client_id, tg_id, tariff_id, new_expiry
    )

    try:
        await xui_call(conn, tg_id, lambda api: _xui_update_client(api, client_id, row["email"], new_expiry, total_gb, tariff["limit_ip"]))
        logger.info("Клиент обновлён в 3x-UI: client_id=%s", client_id)
    except Exception as e:
        logger.error("Ошибка при обновлении клиента в 3x-UI: %s", str(e))
        raise

    await keys_repo.update_expiry(conn, client_id, new_expiry, tariff_id, float(total_gb))
    logger.info("Ключ успешно продлён: client_id=%s", client_id)
    return dict(await keys_repo.get_by_client_id(conn, client_id))


async def create_trial_key(conn: asyncpg.Connection, tg_id: int) -> dict:
    """
    Создать пробный (бесплатный) ключ для пользователя.
    Проверяет, что пользователь ещё не использовал пробный период (trial == 0).
    """
    user = await users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        logger.error("Пользователь не найден: tg_id=%d", tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user["trial"] != 0:
        logger.warning("Пробный период уже использован: tg_id=%d", tg_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trial period already used")

    tariff = await tariffs_repo.get_by_id(conn, settings.default_trial_tariff_id)
    if not tariff:
        logger.error("Пробный тариф не найден: tariff_id=%d", settings.default_trial_tariff_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Trial tariff not configured")

    # Используем create_key для создания самого ключа
    key_data = await create_key(conn, tg_id, settings.default_trial_tariff_id)

    # Отмечаем, что пробный период был использован
    await users_repo.update_trial(conn, tg_id)
    logger.info("Пробный ключ создан: tg_id=%d, client_id=%s", tg_id, key_data["client_id"])

    return key_data
