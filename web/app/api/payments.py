"""Эндпоинты для обработки платежей через backend API.

Все эндпоинты проксируют запросы к backend API.
Webhook-обработка остаётся на уровне web для получения уведомлений от YooKassa.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.core.dependencies import get_current_user, get_backend_client
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
        return []
    logger.info("Получение истории платежей от backend для tg_id=%d", tg_id)
    try:
        payments = await backend.get_payment_history()
        return [PaymentHistoryItem(**p) for p in payments]
    except Exception as e:
        logger.error("Ошибка при получении истории платежей: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Создание платежа через backend: tariff_id=%d", body.tariff_id)
    try:
        payment_data = await backend.create_payment(body.tariff_id, months=1)
        return PaymentResponse(
            payment_id=payment_data["payment_id"],
            payment_url=payment_data["confirmation_url"],
            amount=payment_data["amount"],
        )
    except Exception as e:
        logger.error("Ошибка при создании платежа: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.post("/renew", response_model=PaymentResponse)
async def create_renewal_payment(
    body: RenewPaymentRequest,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Создание платежа продления через backend: client_id=%s, tariff_id=%d",
               body.client_id, body.tariff_id)
    try:
        payment_data = await backend.create_renewal_payment(
            email=body.client_id,
            tariff_id=body.tariff_id,
            months=1
        )
        return PaymentResponse(
            payment_id=payment_data["payment_id"],
            payment_url=payment_data["confirmation_url"],
            amount=payment_data["amount"],
        )
    except Exception as e:
        logger.error("Ошибка при создании платежа продления: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Backend error")


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def check_payment_status(
    payment_id: str,
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    logger.info("Проверка статуса платежа: payment_id=%s", payment_id)
    try:
        payment_status = await backend.get_payment_status(payment_id)
        return PaymentStatusResponse(
            payment_id=payment_status["payment_id"],
            status=payment_status["status"],
            processed=payment_status.get("processed", False),
        )
    except Exception as e:
        logger.error("Ошибка при проверке статуса платежа: %s", str(e))
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
