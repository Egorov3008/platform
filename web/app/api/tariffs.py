"""Публичные эндпоинты для просмотра тарифных планов.

Маршруты не требуют авторизации и доступны любому клиенту.
Админы видят все тарифы, обычные пользователи видят только из AVAILABLE_RATES.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.core.dependencies import get_backend_client_no_auth
from app.core.logging import get_logger
from app.core.security import decode_token
from app.core.config import settings
from app.schemas.tariffs import TariffResponse
from app.api.backend_client import WebBackendClient

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
async def list_tariffs(
    backend: WebBackendClient = Depends(get_backend_client_no_auth),
    is_admin: bool = Depends(get_is_admin),
):
    logger.debug("Fetching tariff list from backend (admin=%s)", is_admin)
    tariffs = await backend.list_tariffs()

    if not is_admin and settings.available_rates:
        tariffs = [t for t in tariffs if t["id"] in settings.available_rates]

    return [TariffResponse(**t) for t in tariffs]


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(
    tariff_id: int,
    backend: WebBackendClient = Depends(get_backend_client_no_auth),
):
    logger.debug("Fetching tariff %d from backend", tariff_id)
    try:
        tariff = await backend.get_tariff(tariff_id)
        return TariffResponse(**tariff)
    except Exception as e:
        logger.debug("Error fetching tariff %d: %s", tariff_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tariff {tariff_id} not found"
        )
