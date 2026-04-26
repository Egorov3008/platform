"""Административные эндпоинты для управления пользователями и ключами.

Предоставляет API для просмотра статистики (dashboard-метрики),
CRUD-операций над пользователями и принудительного удаления ключей.
Все маршруты защищены зависимостью require_admin.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
import asyncpg
from app.core.dependencies import get_conn, require_admin
from app.core.database import get_pool
from app.core.logging import get_logger
from app.schemas.admin import UserPatchRequest, AdminCreateKeyRequest
from app.services import admin as admin_service
from app.services.keys import create_key
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
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение списка пользователей: limit=%d, offset=%d, search=%s", limit, offset, search)
    return await admin_service.get_users(conn, limit, offset, search)


@router.get("/users/{tg_id}")
async def get_user(
    tg_id: int,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение пользователя tg_id=%d", tg_id)
    return await admin_service.get_user(conn, tg_id)


@router.patch("/users/{tg_id}")
async def patch_user(
    tg_id: int,
    body: UserPatchRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.info("Обновление пользователя tg_id=%d: is_blocked=%s, is_admin=%s", tg_id, body.is_blocked, body.is_admin)
    return await admin_service.patch_user(conn, tg_id, body.is_blocked, body.is_admin)


@router.get("/keys")
async def list_keys(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.debug("Получение списка ключей: limit=%d, offset=%d", limit, offset)
    return await admin_service.get_all_keys(conn, limit, offset)


@router.post("/keys")
async def admin_create_key(
    body: AdminCreateKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.info("Админ создаёт ключ для tg_id=%d, tariff_id=%d", body.tg_id, body.tariff_id)
    return await create_key(conn, body.tg_id, body.tariff_id)


@router.delete("/keys/{client_id}", status_code=204)
async def admin_delete_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    logger.info("Админ удаляет ключ client_id=%s", client_id)
    await admin_service.admin_force_delete_key(conn, client_id)
