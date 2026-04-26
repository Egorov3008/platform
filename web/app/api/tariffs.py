"""Публичные эндпоинты для просмотра тарифных планов.

Маршруты не требуют авторизации и доступны любому клиенту.
Админы видят все тарифы, обычные пользователи видят только из AVAILABLE_RATES.
"""

from fastapi import APIRouter, Depends, Request
import asyncpg
from app.core.dependencies import get_conn
from app.core.logging import get_logger
from app.core.security import decode_token
from app.schemas.tariffs import TariffResponse
from app.services import tariffs as tariff_service

router = APIRouter()
logger = get_logger(__name__)


def get_is_admin(request: Request) -> bool:
    """Проверить статус администратора из JWT токена если есть."""
    token = request.cookies.get("access_token")
    if not token:
        return False
    try:
        payload = decode_token(token)
        return payload.get("is_admin", False)
    except ValueError:
        return False


@router.get("/", response_model=list[TariffResponse])
async def list_tariffs(conn: asyncpg.Connection = Depends(get_conn), is_admin: bool = Depends(get_is_admin)):
    logger.debug("Получение списка тарифов (admin=%s)", is_admin)
    return await tariff_service.get_all(conn, is_admin=is_admin)


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: int, conn: asyncpg.Connection = Depends(get_conn)):
    logger.debug("Получение тарифа tariff_id=%d", tariff_id)
    return await tariff_service.get_by_id(conn, tariff_id)
