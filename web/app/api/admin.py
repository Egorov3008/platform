"""Административные эндпоинты для управления пользователями и ключами.

Предоставляет API для просмотра статистики (dashboard-метрики),
CRUD-операций над пользователями и операций с ключами через backend API.
Все маршруты защищены зависимостью require_admin.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from app.api.backend_client import WebBackendClient
from app.core.dependencies import require_admin, get_backend_client
from app.core.database import get_pool
from app.core.logging import get_logger
from app.schemas.admin import UserPatchRequest, AdminCreateKeyRequest
from app.services.dashboard_metrics import DashboardMetricsService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/stats")
async def stats(_: dict = Depends(require_admin)):
    logger.info("Получение статистики dashboard")
    pool = get_pool()
    svc = DashboardMetricsService(pool)
    metrics = await svc.get_all_dashboard_metrics()
    return {
        "mrr_current_month": metrics.mrr_current_month,
        "mrr_previous_month": metrics.mrr_previous_month,
        "mrr_growth": metrics.mrr_growth,
        "paying_users_current": metrics.paying_users_current,
        "total_new_users_30d": metrics.total_new_users_30d,
        "conversion_to_keys_pct": metrics.conversion_to_keys_pct,
        "conversion_to_paid_pct": metrics.conversion_to_paid_pct,
        "total_expiring_72h": metrics.total_expiring_72h,
        "total_succeeded": metrics.total_succeeded,
        "succeeded_pct": metrics.succeeded_pct,
    }


@router.get("/users")
async def list_users(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    search: Optional[str] = Query(None),
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение списка пользователей: limit=%d, offset=%d, search=%s", limit, offset, search)
    try:
        users = await backend.list_admin_users()
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in str(u.get("tg_id", ""))
                or search_lower in (u.get("username") or "").lower()
                or search_lower in (u.get("first_name") or "").lower()
            ]
        return users[offset:offset + limit]
    except Exception as e:
        logger.error("Failed to list users from backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.get("/users/{tg_id}")
async def get_user(
    tg_id: int,
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение пользователя tg_id=%d", tg_id)
    try:
        return await backend.get_user(tg_id)
    except Exception as e:
        logger.error("Failed to get user tg_id=%d from backend: %s", tg_id, str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.patch("/users/{tg_id}")
async def patch_user(
    tg_id: int,
    body: UserPatchRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.info("Обновление пользователя tg_id=%d: is_blocked=%s", tg_id, body.is_blocked)
    try:
        return await backend.patch_admin_user(tg_id, body.is_blocked)
    except Exception as e:
        logger.error("Failed to patch user tg_id=%d via backend: %s", tg_id, str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.get("/keys")
async def list_keys(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение списка ключей через backend: limit=%d, offset=%d", limit, offset)
    try:
        keys = await backend.list_keys()
        return keys[offset:offset+limit]
    except Exception as e:
        logger.error("Failed to list keys from backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.post("/keys")
async def admin_create_key(
    body: AdminCreateKeyRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.info("Админ создаёт ключ для tg_id=%d, tariff_id=%d", body.tg_id, body.tariff_id)
    try:
        key_data = await backend.create_key(body.tariff_id)
        return key_data
    except Exception as e:
        logger.error("Failed to create key via backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")


@router.delete("/keys/{email:path}", status_code=204)
async def admin_delete_key(
    email: str,
    backend: WebBackendClient = Depends(get_backend_client),
    _: dict = Depends(require_admin),
):
    logger.info("Админ удаляет ключ email=%s", email)
    try:
        await backend.delete_key(email)
    except Exception as e:
        logger.error("Failed to delete key via backend: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
