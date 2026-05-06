"""Эндпоинты для обработки платежей через backend API.

Все эндпоинты проксируют запросы к backend API.
Webhook-обработка остаётся на уровне web для получения уведомлений от YooKassa.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.core.dependencies import get_current_user, get_backend_client
from app.core.config import settings
from app.core.logging import get_logger
from app.api.backend_client import WebBackendClient
from app.schemas.payments import (
    CreatePaymentRequest, PaymentResponse,
    RenewPaymentRequest, PaymentHistoryItem, PaymentStatusResponse
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=list[PaymentHistoryItem])
async def list_payments(
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        logger.debug("tg_id отсутствует, возвращаем пустой список")
        return []
    logger.debug("GET /payments: запрос истории платежей", extra={"tg_id": tg_id})
    try:
        payments = await backend.get_payment_history()
        logger.debug("GET /payments: успешно получено платежей", extra={"count": len(payments), "tg_id": tg_id})
        items = []
        for i, p in enumerate(payments):
            try:
                item = PaymentHistoryItem(**p)
                items.append(item)
            except Exception as e:
                logger.error(
                    f"GET /payments: ошибка при создании item {i}",
                    extra={"payment": p, "error": str(e), "index": i},
                    exc_info=True
                )
                raise
        return sorted(items, key=lambda x: x.created_at or datetime.min, reverse=True)
    except Exception as e:
        logger.error(
            "GET /payments: ошибка при получении истории платежей",
            extra={"error": str(e), "tg_id": tg_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        logger.warning("POST /payments/create: tg_id отсутствует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.debug("POST /payments/create: запрос", extra={"tg_id": tg_id, "tariff_id": body.tariff_id, "months": body.number_of_months})
    try:
        payment_data = await backend.create_payment(body.tariff_id, months=body.number_of_months)
        logger.debug("POST /payments/create: успешное создание платежа", extra={"payment_id": payment_data["payment_id"], "amount": payment_data.get("amount")})
        return PaymentResponse(
            payment_id=payment_data["payment_id"],
            payment_url=payment_data["confirmation_url"],
            amount=payment_data["amount"],
        )
    except Exception as e:
        logger.error(
            "POST /payments/create: ошибка при создании платежа",
            extra={"error": str(e), "tg_id": tg_id, "tariff_id": body.tariff_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.post("/renew", response_model=PaymentResponse)
async def create_renewal_payment(
    body: RenewPaymentRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        logger.warning("POST /payments/renew: tg_id отсутствует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.debug("POST /payments/renew: запрос", extra={"tg_id": tg_id, "email": body.client_id, "tariff_id": body.tariff_id, "months": body.number_of_months})
    try:
        payment_data = await backend.create_renewal_payment(
            email=body.client_id,
            tariff_id=body.tariff_id,
            months=body.number_of_months
        )
        logger.debug("POST /payments/renew: успешное создание платежа продления", extra={"payment_id": payment_data["payment_id"], "amount": payment_data.get("amount")})
        return PaymentResponse(
            payment_id=payment_data["payment_id"],
            payment_url=payment_data["confirmation_url"],
            amount=payment_data["amount"],
        )
    except Exception as e:
        logger.error(
            "POST /payments/renew: ошибка при создании платежа продления",
            extra={"error": str(e), "tg_id": tg_id, "email": body.client_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.get("/config")
async def payment_config():
    """Get payment configuration for frontend (no auth required).

    This endpoint is used by the frontend to get discount information
    before the user is logged in (e.g., on the tariffs page).
    """
    logger.debug("Получена конфигурация платежей")
    return {"volume_discount_percent": settings.discounts}


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def check_payment_status(
    payment_id: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        logger.warning("GET /payments/{payment_id}/status: tg_id отсутствует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.debug("GET /payments/{payment_id}/status: запрос", extra={"payment_id": payment_id, "tg_id": tg_id})
    try:
        payment_status = await backend.get_payment_status(payment_id)
        status_val = payment_status.get("status", "")
        processed = status_val not in ["pending", "processing"]
        logger.debug("GET /payments/{payment_id}/status: успешно получен статус платежа", extra={"payment_id": payment_id, "status": status_val, "processed": processed})
        return PaymentStatusResponse(
            payment_id=payment_status["payment_id"],
            status=status_val,
            processed=processed,
        )
    except Exception as e:
        logger.error(
            "GET /payments/{payment_id}/status: ошибка при проверке статуса платежа",
            extra={"error": str(e), "payment_id": payment_id, "tg_id": tg_id, "error_type": type(e).__name__},
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Webhook от YooKassa.

    Сейчас просто логируем и возвращаем 200 OK.
    Backend обрабатывает уведомления отдельно если нужно.
    """
    logger.info("Получен webhook от YooKassa")
    try:
        body = await request.body()
        logger.debug("Webhook payload size: %d bytes", len(body))
    except Exception as e:
        logger.error("Ошибка при чтении тела webhook: %s", str(e))
    logger.info("Webhook обработан (204 OK возвращён YooKassa)")
    return {"status": "ok"}
