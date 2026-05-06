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
    logger.debug("GET /tariffs: запрос списка тарифов", extra={"is_admin": is_admin})
    try:
        tariffs = await backend.list_tariffs()
        logger.debug("GET /tariffs: успешно получено тарифов", extra={"count": len(tariffs), "is_admin": is_admin})

        if not is_admin and settings.available_rates:
            tariffs = [t for t in tariffs if t["id"] in settings.available_rates]
            logger.debug("GET /tariffs: отфильтрованы доступные тарифы", extra={"count": len(tariffs)})

        return [TariffResponse(**t) for t in tariffs]
    except Exception as e:
        logger.error(
            "GET /tariffs: ошибка при получении списка тарифов",
            extra={"error": str(e), "is_admin": is_admin, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(
    tariff_id: int,
    backend: WebBackendClient = Depends(get_backend_client_no_auth),
):
    logger.debug("GET /tariffs/{tariff_id}: запрос тарифа", extra={"tariff_id": tariff_id})
    try:
        tariff = await backend.get_tariff(tariff_id)
        logger.debug("GET /tariffs/{tariff_id}: тариф успешно получен", extra={"tariff_id": tariff_id})
        return TariffResponse(**tariff)
    except Exception as e:
        logger.error(
            "GET /tariffs/{tariff_id}: ошибка при получении тарифа",
            extra={"error": str(e), "tariff_id": tariff_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tariff {tariff_id} not found"
        )
