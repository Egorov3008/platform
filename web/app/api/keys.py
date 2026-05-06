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
    tg_id = _require_tg_id(current_user)
    logger.debug("GET /keys: запрос списка ключей", extra={"tg_id": tg_id})
    try:
        keys = await backend.list_keys()
        logger.debug("GET /keys: успешно получено ключей", extra={"count": len(keys), "tg_id": tg_id})
        return [KeyResponse(**k) for k in keys]
    except Exception as e:
        logger.error(
            "GET /keys: ошибка при получении списка ключей",
            extra={"error": str(e), "tg_id": tg_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.post("/", response_model=KeyResponse)
async def create_key(
    body: CreateKeyRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("POST /keys: создание ключа", extra={"tg_id": tg_id, "tariff_id": body.tariff_id})
    try:
        key_data = await backend.create_key(body.tariff_id)
        logger.info("POST /keys: ключ успешно создан", extra={"tg_id": tg_id, "email": key_data.get("email")})
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error(
            "POST /keys: ошибка при создании ключа",
            extra={"error": str(e), "tg_id": tg_id, "tariff_id": body.tariff_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.get("/{email:path}", response_model=KeyResponse)
async def get_key(
    email: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.debug("GET /keys/{email}: получение ключа", extra={"tg_id": tg_id, "email": email})
    try:
        key_data = await backend.get_key(email)
        logger.debug("GET /keys/{email}: ключ успешно получен", extra={"tg_id": tg_id, "email": email})
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error(
            "GET /keys/{email}: ошибка при получении ключа",
            extra={"error": str(e), "tg_id": tg_id, "email": email, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.post("/{email:path}/renew", response_model=KeyResponse)
async def renew_key(
    email: str,
    body: RenewKeyRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("POST /keys/{email}/renew: продление ключа", extra={"tg_id": tg_id, "email": email, "tariff_id": body.tariff_id})
    try:
        key_data = await backend.renew_key(email, tg_id, body.tariff_id, months=1)
        logger.info("POST /keys/{email}/renew: ключ успешно продлён", extra={"tg_id": tg_id, "email": email})
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error(
            "POST /keys/{email}/renew: ошибка при продлении ключа",
            extra={"error": str(e), "tg_id": tg_id, "email": email, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.delete("/{email:path}", status_code=204)
async def delete_key(
    email: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("DELETE /keys/{email}: удаление ключа", extra={"tg_id": tg_id, "email": email})
    try:
        await backend.delete_key(email)
        logger.info("DELETE /keys/{email}: ключ успешно удалён", extra={"tg_id": tg_id, "email": email})
    except Exception as e:
        logger.error(
            "DELETE /keys/{email}: ошибка при удалении ключа",
            extra={"error": str(e), "tg_id": tg_id, "email": email, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
