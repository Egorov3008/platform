"""Эндпоинты для обработки платежей через YooKassa.

Включает создание платежа (с редиректом на оплату) и webhook
для обработки уведомлений от платёжной системы.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.core.logging import get_logger
from app.schemas.payments import (
    CreatePaymentRequest, PaymentResponse,
    RenewPaymentRequest, PaymentHistoryItem, PaymentStatusResponse
)
from app.services import payments as payment_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=list[PaymentHistoryItem])
async def list_payments(
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        return []
    logger.info("Получение истории платежей для tg_id=%d", tg_id)
    return await payment_service.get_user_payments(conn, tg_id)


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Создание платежа для tg_id=%d, tariff_id=%d", tg_id, body.tariff_id)
    return await payment_service.create_payment(conn, tg_id, body.tariff_id)


@router.post("/renew", response_model=PaymentResponse)
async def create_renewal_payment(
    body: RenewPaymentRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Создание платежа продления для tg_id=%d, client_id=%s, tariff_id=%d",
               tg_id, body.client_id, body.tariff_id)
    return await payment_service.create_renewal_payment(conn, tg_id, body.client_id, body.tariff_id)


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def check_payment_status(
    payment_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Проверка статуса платежа: payment_id=%s, tg_id=%d", payment_id, tg_id)
    return await payment_service.get_payment_status(conn, payment_id, tg_id)


@router.post("/webhook")
async def payment_webhook(request: Request, conn: asyncpg.Connection = Depends(get_conn)):
    logger.info("Получен webhook от YooKassa")
    body = await request.body()
    await payment_service.handle_webhook(conn, body, request)
    logger.info("Webhook от YooKassa успешно обработан")
    return {"status": "ok"}
