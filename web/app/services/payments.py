"""Сервис обработки платежей через YooKassa.

Создаёт платежи с редиректом на оплату, обрабатывает webhook-уведомления
и автоматически создаёт VPN-ключ при успешной оплате.
"""

import asyncio
import asyncpg
import uuid
from fastapi import HTTPException, Request, status
from yookassa import Configuration, Payment
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import WebhookNotificationFactory, WebhookNotificationEventType
from app.repositories.payments import PaymentsRepo
from app.repositories.tariffs import TariffsRepo
from app.repositories.users import UsersRepo
from app.repositories.stocks import StocksRepo
from app.core.config import settings
from app.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)

Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key

payments_repo = PaymentsRepo()
tariffs_repo = TariffsRepo()
users_repo = UsersRepo()

# payment_type formats:
# - Web: "web_new_key|{tg_id}:{tariff_id}" или "web_renew_key|{client_id}:{tariff_id}"
# - Bot: "create_key|{tariff_id}" или "renew_key|{email}"
_OPERATION_NEW_KEY = "web_new_key"
_OPERATION_RENEW_KEY = "web_renew_key"
_OPERATION_BOT_NEW_KEY = "create_key"
_OPERATION_BOT_RENEW_KEY = "renew_key"


async def create_payment(conn: asyncpg.Connection, tg_id: int, tariff_id: int) -> dict:
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        logger.error("Тариф не найден: tariff_id=%d", tariff_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    if tariff["amount"] <= 0:
        logger.warning(
            "Попытка создать платёж для бесплатного тарифа: tariff_id=%d, amount=%f",
            tariff_id, tariff["amount"]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tariff '{tariff['name_tariff']}' is free (amount=0). Cannot create payment for free tariffs.",
        )

    idempotence_key = str(uuid.uuid4())
    logger.info(
        "Создание платежа: tg_id=%d, tariff_id=%d, amount=%f",
        tg_id, tariff_id, tariff["amount"]
    )
    payment = await asyncio.to_thread(
        Payment.create,
        {
            "amount": {"value": f"{tariff['amount']:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.webhook_base_url}/payment/success",
            },
            "capture": True,
            "description": f"VPN: {tariff['name_tariff']}",
        },
        idempotence_key,
    )

    payment_type = f"{_OPERATION_NEW_KEY}|{tg_id}:{tariff_id}"
    await payments_repo.create(
        conn,
        payment_id=payment.id,
        tg_id=tg_id,
        amount=tariff["amount"],
        payment_type=payment_type,
        status="pending",
    )

    logger.info("Платёж создан: payment_id=%s для tg_id=%d", payment.id, tg_id)
    return {
        "payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "amount": tariff["amount"],
    }


async def _handle_succeeded(conn: asyncpg.Connection, payment_obj) -> None:
    payment_id = payment_obj.id
    existing = await payments_repo.get_by_payment_id(conn, payment_id)
    if not existing or existing["status"] in ("succeeded", "processing"):
        logger.debug("Платёж уже обработан или не найден: payment_id=%s", payment_id)
        return

    logger.info("Обработка успешного платежа: payment_id=%s", payment_id)

    payment_type = existing["payment_type"] or ""
    if "|" not in payment_type:
        logger.warning("Некорректный payment_type: %s", payment_type)
        await payments_repo.update_status(conn, payment_id, "succeeded")
        return

    operation, data = payment_type.split("|", 1)
    tg_id = existing["tg_id"]

    # Web format: "web_new_key|{tg_id}:{tariff_id}" или "web_renew_key|{client_id}:{tariff_id}"
    if operation == _OPERATION_NEW_KEY and ":" in data:
        _, tariff_id_str = data.split(":", 1)
        try:
            tariff_id = int(tariff_id_str)
            from app.services.keys import create_key
            logger.info("Создание нового ключа (web): tg_id=%d, tariff_id=%d", tg_id, tariff_id)
            await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
        except Exception as e:
            logger.error("Ошибка при создании ключа: payment_id=%s, error=%s", payment_id, str(e))
            await payments_repo.update_status(conn, payment_id, "key_creation_failed")
            return

    elif operation == _OPERATION_RENEW_KEY and ":" in data:
        client_id, tariff_id_str = data.split(":", 1)
        try:
            tariff_id = int(tariff_id_str)
            from app.services.keys import renew_key
            logger.info("Продление ключа (web): client_id=%s, tg_id=%d, tariff_id=%d", client_id, tg_id, tariff_id)
            await renew_key(conn, client_id=client_id, tg_id=tg_id, tariff_id=tariff_id)
        except Exception as e:
            logger.error("Ошибка при продлении ключа: payment_id=%s, error=%s", payment_id, str(e))
            await payments_repo.update_status(conn, payment_id, "key_creation_failed")
            return

    # Bot format: "create_key|{tariff_id}" или "renew_key|{email}"
    elif operation == _OPERATION_BOT_NEW_KEY:
        try:
            tariff_id = int(data)
            from app.services.keys import create_key
            logger.info("Создание нового ключа (bot): tg_id=%d, tariff_id=%d", tg_id, tariff_id)
            await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
        except Exception as e:
            logger.error("Ошибка при создании ключа (bot): payment_id=%s, error=%s", payment_id, str(e))
            await payments_repo.update_status(conn, payment_id, "key_creation_failed")
            return

    elif operation == _OPERATION_BOT_RENEW_KEY:
        email = data
        try:
            from app.repositories.keys import KeysRepo
            key_repo = KeysRepo()
            key_row = await key_repo.get_by_email(conn, email)
            if not key_row:
                logger.error("Ключ не найден по email: email=%s", email)
                await payments_repo.update_status(conn, payment_id, "key_not_found")
                return

            from app.services.keys import renew_key
            logger.info("Продление ключа (bot): email=%s, tg_id=%d, tariff_id=%d", email, tg_id, key_row["tariff_id"])
            await renew_key(conn, client_id=key_row["client_id"], tg_id=tg_id, tariff_id=key_row["tariff_id"])
        except Exception as e:
            logger.error("Ошибка при продлении ключа (bot): payment_id=%s, error=%s", payment_id, str(e))
            await payments_repo.update_status(conn, payment_id, "key_creation_failed")
            return

    else:
        logger.warning("Неизвестная операция: %s", operation)

    # Обработка реферального бонуса (если применялась реферальная скидка)
    payment_amount = existing.get("amount", 0.0)
    if payment_amount > 0:
        try:
            from app.services.referral import ReferralService
            from app.repositories.referral import ReferralRepo
            referral_repo = ReferralRepo()
            referral_service = ReferralService(referral_repo, users_repo)
            await referral_service.process_referral_bonus(conn, tg_id, payment_amount)
        except Exception as e:
            logger.error("Ошибка при обработке реферального бонуса: payment_id=%s, error=%s", payment_id, str(e))

    # Вычитание реферальной скидки из баланса пользователя
    referral_discount = existing.get("referral_discount", 0.0)
    if referral_discount > 0:
        try:
            await users_repo.update_balance(conn, tg_id, -referral_discount)
            logger.info("Реферальная скидка вычтена: tg_id=%d, amount=%f", tg_id, referral_discount)
        except Exception as e:
            logger.error("Ошибка при вычитании реферальной скидки: payment_id=%s, error=%s", payment_id, str(e))

    await payments_repo.update_status(conn, payment_id, "succeeded")


async def _handle_waiting_for_capture(conn: asyncpg.Connection, payment_obj) -> None:
    payment_id = payment_obj.id
    logger.info("Обработка waiting_for_capture: payment_id=%s", payment_id)
    await payments_repo.update_status(conn, payment_id, "processing")

    try:
        amount_value = payment_obj.amount.value
        idempotence_key = str(uuid.uuid4())
        await asyncio.to_thread(
            Payment.capture,
            payment_id,
            {"amount": {"value": f"{float(amount_value):.2f}", "currency": "RUB"}},
            idempotence_key,
        )
        logger.info("Платёж успешно подтверждён (capture): payment_id=%s", payment_id)
    except Exception as e:
        logger.error("Ошибка при подтверждении платежа: payment_id=%s, error=%s", payment_id, str(e))


async def _handle_canceled(conn: asyncpg.Connection, payment_obj) -> None:
    payment_id = payment_obj.id
    existing = await payments_repo.get_by_payment_id(conn, payment_id)
    if not existing or existing["status"] == "canceled":
        logger.debug("Платёж уже отменён: payment_id=%s", payment_id)
        return

    reason = getattr(getattr(payment_obj, "cancellation_details", None), "reason", "unknown")
    logger.warning("Платёж отменён: payment_id=%s, reason=%s", payment_id, reason)
    await payments_repo.update_status(conn, payment_id, "canceled")


async def handle_webhook(conn: asyncpg.Connection, body: bytes, request: Request) -> None:
    # Проверка IP YooKassa (можно отключить через DISABLE_WEBHOOK_IP_CHECK=true)
    if not settings.disable_webhook_ip_check:
        ip = request.client.host
        if not SecurityHelper().is_ip_trusted(ip):
            logger.warning("Webhook от непроверенного IP: %s", ip)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Untrusted IP")

    try:
        import json
        event_json = json.loads(body)
        notification = WebhookNotificationFactory().create(event_json)
        logger.info("Получено уведомление от YooKassa: event=%s, payment_id=%s",
                   notification.event, notification.object.id if hasattr(notification, 'object') else 'N/A')
    except Exception as e:
        logger.error("Ошибка при обработке webhook: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    event_handlers = {
        WebhookNotificationEventType.PAYMENT_SUCCEEDED: _handle_succeeded,
        WebhookNotificationEventType.PAYMENT_WAITING_FOR_CAPTURE: _handle_waiting_for_capture,
        WebhookNotificationEventType.PAYMENT_CANCELED: _handle_canceled,
    }

    handler = event_handlers.get(notification.event)
    if handler:
        try:
            await handler(conn, notification.object)
        except Exception as e:
            logger.error("Ошибка при обработке события %s: %s", notification.event, str(e))
    else:
        logger.debug("Игнорирование события: %s", notification.event)


async def create_renewal_payment(conn: asyncpg.Connection, tg_id: int, client_id: str, tariff_id: int) -> dict:
    from app.repositories.keys import KeysRepo

    key_repo = KeysRepo()
    key_row = await key_repo.get_by_client_id(conn, client_id)
    if not key_row or key_row["tg_id"] != tg_id:
        logger.warning("Попытка создать платёж продления для чужого ключа: tg_id=%d, client_id=%s", tg_id, client_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        logger.error("Тариф не найден: tariff_id=%d", tariff_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    if tariff["amount"] <= 0:
        logger.warning("Попытка создать платёж продления для бесплатного тарифа: tariff_id=%d", tariff_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pay for free tariff")

    idempotence_key = str(uuid.uuid4())
    logger.info("Создание платежа продления: tg_id=%d, client_id=%s, tariff_id=%d, amount=%f",
               tg_id, client_id, tariff_id, tariff["amount"])

    payment = await asyncio.to_thread(
        Payment.create,
        {
            "amount": {"value": f"{tariff['amount']:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.webhook_base_url}/payment/success",
            },
            "capture": True,
            "description": f"VPN продление: {tariff['name_tariff']}",
        },
        idempotence_key,
    )

    payment_type = f"{_OPERATION_RENEW_KEY}|{client_id}:{tariff_id}"
    await payments_repo.create(
        conn,
        payment_id=payment.id,
        tg_id=tg_id,
        amount=tariff["amount"],
        payment_type=payment_type,
        status="pending",
    )

    logger.info("Платёж продления создан: payment_id=%s", payment.id)
    return {
        "payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "amount": tariff["amount"],
    }


async def get_payment_status(conn: asyncpg.Connection, payment_id: str, tg_id: int) -> dict:
    existing = await payments_repo.get_by_payment_id(conn, payment_id)
    if not existing or existing["tg_id"] != tg_id:
        logger.warning("Попытка проверить статус чужого платежа: payment_id=%s, tg_id=%d", payment_id, tg_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    logger.info("Проверка статуса платежа в YooKassa: payment_id=%s", payment_id)
    yoo_payment = await asyncio.to_thread(Payment.find_one, payment_id)
    yoo_status = getattr(yoo_payment, "status", None) or getattr(yoo_payment, "_status", None)

    processed = False
    if yoo_status == "succeeded" and existing["status"] not in ("succeeded", "processing"):
        logger.info("Платёж подтверждён в YooKassa, обрабатываем: payment_id=%s", payment_id)
        await _handle_succeeded(conn, yoo_payment)
        processed = True

    return {
        "payment_id": payment_id,
        "status": yoo_status or existing["status"],
        "processed": processed,
    }


async def get_user_payments(conn: asyncpg.Connection, tg_id: int) -> list[dict]:
    rows = await payments_repo.get_by_tg_id(conn, tg_id)
    return [dict(r) for r in rows]


async def create_bot_payment(
    conn: asyncpg.Connection,
    tg_id: int,
    tariff_id: int,
    months: int = 1,
    email: Optional[str] = None,
) -> dict:
    """
    Создать платёж для бота.

    Поддерживает:
    - Новый ключ: tariff_id, months (опционально)
    - Продление: email, months (опционально)

    Применяет: персональную скидку, объёмную скидку, реферальную скидку.
    """
    from app.services.pricing import PricingService

    # Если email передан, это продление
    is_renewal = email is not None

    if is_renewal:
        # Продление: проверяем, что ключ существует
        from app.repositories.keys import KeysRepo
        key_repo = KeysRepo()
        key_row = await key_repo.get_by_email(conn, email)
        if not key_row or key_row["tg_id"] != tg_id:
            logger.warning("Ключ не найден при создании платежа продления: email=%s, tg_id=%d", email, tg_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
        actual_tariff_id = key_row["tariff_id"]
    else:
        actual_tariff_id = tariff_id

    tariff = await tariffs_repo.get_by_id(conn, actual_tariff_id)
    if not tariff:
        logger.error("Тариф не найден: tariff_id=%d", actual_tariff_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    if tariff["amount"] <= 0:
        logger.warning("Попытка создать платёж для бесплатного тарифа: tariff_id=%d", actual_tariff_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create payment for free tariff")

    # Рассчитать цену с учётом скидок
    pricing_service = PricingService(tariffs_repo, StocksRepo())
    price_result = await pricing_service.calculate_price(conn, tg_id, actual_tariff_id, months)

    # Получить баланс пользователя (реферальная скидка)
    user = await users_repo.get_by_tg_id(conn, tg_id)
    referral_discount = 0.0
    if user and user["balance"] > 0:
        # Используем реферальный баланс до размера финальной цены
        referral_discount = min(user["balance"], price_result.final_amount * months)

    final_payment_amount = (price_result.final_amount * months) - referral_discount

    idempotence_key = str(uuid.uuid4())
    logger.info(
        "Создание платежа бота: tg_id=%d, tariff_id=%d, months=%d, amount=%f (с реф.скидкой %f)",
        tg_id, actual_tariff_id, months, final_payment_amount, referral_discount
    )

    payment = await asyncio.to_thread(
        Payment.create,
        {
            "amount": {"value": f"{final_payment_amount:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.webhook_base_url}/payment/success",
            },
            "capture": True,
            "description": f"VPN {'продление' if is_renewal else 'новый ключ'}: {tariff['name_tariff']}",
        },
        idempotence_key,
    )

    # Формат платежа зависит от типа операции
    if is_renewal:
        payment_type = f"{_OPERATION_BOT_RENEW_KEY}|{email}"
    else:
        payment_type = f"{_OPERATION_BOT_NEW_KEY}|{actual_tariff_id}"

    await payments_repo.create(
        conn,
        payment_id=payment.id,
        tg_id=tg_id,
        amount=final_payment_amount,
        payment_type=payment_type,
        status="pending",
        number_of_months=months,
        discount_percent=int(price_result.discount_percent) if price_result.has_discount else 0,
        referral_discount=referral_discount,
    )

    logger.info("Платёж бота создан: payment_id=%s", payment.id)
    return {
        "payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "amount": final_payment_amount,
        "original_amount": price_result.original_amount * months,
        "discount_percent": price_result.discount_percent,
        "referral_discount": referral_discount,
    }
