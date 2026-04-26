"""Эндпоинты управления VPN-ключами для авторизованных пользователей.

Позволяет создавать, просматривать, продлевать и удалять ключи.
Все операции привязаны к tg_id текущего пользователя.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.core.logging import get_logger
from app.schemas.keys import KeyResponse, CreateKeyRequest, RenewKeyRequest
from app.services import keys as keys_service
from app.repositories.tariffs import TariffsRepo

_tariffs_repo = TariffsRepo()

router = APIRouter()
logger = get_logger(__name__)


def _require_tg_id(current_user: dict) -> int:
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram account required to manage keys",
        )
    return tg_id


@router.get("/", response_model=list[KeyResponse])
async def list_keys(
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        return []
    logger.debug("Получение ключей для tg_id=%d", tg_id)
    return await keys_service.get_user_keys(conn, tg_id)


@router.post("/", response_model=KeyResponse)
async def create_key(
    body: CreateKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    # WR-04: прямое создание ключа разрешено только для бесплатных тарифов
    tariff = await _tariffs_repo.get_by_id(conn, body.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    if tariff["amount"] > 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Paid tariffs require payment via /payments/create",
        )
    logger.info("Создание нового ключа для tg_id=%d, tariff_id=%d", tg_id, body.tariff_id)
    return await keys_service.create_key(conn, tg_id, body.tariff_id)


@router.get("/{client_id}", response_model=KeyResponse)
async def get_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    keys = await keys_service.get_user_keys(conn, tg_id)
    key = next((k for k in keys if k["client_id"] == client_id), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    logger.debug("Получение ключа client_id=%s для tg_id=%d", client_id, tg_id)
    return key


@router.post("/{client_id}/renew", response_model=KeyResponse)
async def renew_key(
    client_id: str,
    body: RenewKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    tariff = await _tariffs_repo.get_by_id(conn, body.tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    if tariff["amount"] > 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Paid renewal requires payment via /payments/renew",
        )
    logger.info("Продление ключа client_id=%s для tg_id=%d, tariff_id=%d (бесплатный тариф)",
               client_id, tg_id, body.tariff_id)
    return await keys_service.renew_key(conn, client_id, tg_id, body.tariff_id)


@router.delete("/{client_id}", status_code=204)
async def delete_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("Удаление ключа client_id=%s для tg_id=%d", client_id, tg_id)
    await keys_service.delete_key(conn, client_id, tg_id)
