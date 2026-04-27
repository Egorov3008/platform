"""Эндпоинты управления VPN-ключами для авторизованных пользователей.

Позволяет создавать, просматривать, продлевать и удалять ключи.
Все операции привязаны к tg_id текущего пользователя через backend API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.backend_client import WebBackendClient
from app.core.dependencies import get_backend_client, get_current_user
from app.core.logging import get_logger
from app.schemas.keys import KeyResponse, CreateKeyRequest, RenewKeyRequest

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
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    _require_tg_id(current_user)
    logger.debug("Fetching user keys from backend")
    try:
        keys = await backend.list_keys()
        return [KeyResponse(**k) for k in keys]
    except Exception as e:
        logger.error("Failed to list keys from backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.post("/", response_model=KeyResponse)
async def create_key(
    body: CreateKeyRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("Creating key via backend: tariff_id=%d", body.tariff_id)
    try:
        key_data = await backend.create_key(body.tariff_id)
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error("Failed to create key via backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.get("/{email:path}", response_model=KeyResponse)
async def get_key(
    email: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    _require_tg_id(current_user)
    logger.debug("Fetching key for email=%s", email)
    try:
        key_data = await backend.get_key(email)
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error("Failed to get key from backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.post("/{email:path}/renew", response_model=KeyResponse)
async def renew_key(
    email: str,
    body: RenewKeyRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("Renewing key via backend: email=%s, tariff_id=%d", email, body.tariff_id)
    try:
        # Note: months parameter defaults to 1; could be extended via RenewKeyRequest if needed
        key_data = await backend.renew_key(email, body.tariff_id, months=1)
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error("Failed to renew key via backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.delete("/{email:path}", status_code=204)
async def delete_key(
    email: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("Deleting key via backend: email=%s", email)
    try:
        await backend.delete_key(email)
    except Exception as e:
        logger.error("Failed to delete key via backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
