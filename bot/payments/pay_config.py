import asyncio
import uuid
from typing import Dict, Optional, Any

from yookassa import Payment, Configuration

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, URL_BOT
from logger import logger

# Настройка конфигурации YooKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


class YooKassService:
    """Сервис для работы с YooKassa."""

    def _data_payment(self, price: float, description: str) -> dict:
        """Формирует данные для создания платежа."""
        return {
            "amount": {"value": f"{float(price):.2f}", "currency": "RUB"},
            "payment_method_data": {"type": "bank_card"},
            "confirmation": {"type": "redirect", "return_url": URL_BOT},
            "description": description,
            "capture": False,
            "receipt": {
                "customer": {"email": "egorov3008@example.com"},
                "items": [
                    {
                        "description": "Услуги ИТ",
                        "quantity": "1",
                        "amount": {"value": f"{price:.2f}", "currency": "RUB"},
                        "vat_code": "1",
                        "payment_mode": "full_payment",
                        "payment_subject": "service",
                    }
                ],
            },
        }

    async def _create_payment(
        self, price: float, payment_data: dict[str, Any], idempotence_key: str
    ) -> Dict[str, str]:
        try:
            payment = await asyncio.to_thread(Payment.create, payment_data, idempotence_key)

            # ПРАВИЛЬНОЕ ПОЛУЧЕНИЕ confirmation_url
            confirmation_url = None
            if hasattr(payment, "confirmation") and payment.confirmation:
                confirmation_url = payment.confirmation.confirmation_url
            elif hasattr(payment, "confirmations") and payment.confirmations:
                # Иногда confirmation может быть списком
                confirmation_url = payment.confirmations[0].confirmation_url

            if not confirmation_url:
                logger.error(
                    "Confirmation URL не найден в ответе платежа",
                    payment_id=payment.id,
                    payment_attributes=dir(payment),
                )
                raise ValueError("Confirmation URL not found in payment response")

            logger.info(
                "Платеж успешно создан",
                payment_id=payment.id,
                amount=price,
                confirmation_url=confirmation_url,
            )

            return {"payment_id": payment.id, "confirmation_url": confirmation_url}

        except Exception as e:
            logger.error(
                "Ошибка создания платежа",
                exc_info=True,
                amount=price,
                idempotence_key=idempotence_key,
                error_type=type(e).__name__,
            )

            if hasattr(e, "response"):
                logger.debug(
                    "Детали ошибки API",
                    status_code=getattr(e.response, "status_code", None),
                    response_text=getattr(e.response, "text", "")[:200],
                )
            raise

    async def create_payment_form(self, price: float, description: str) -> Dict[str, str]:
        """
        Создает новый платеж и возвращает его идентификатор и URL для подтверждения.

        Args:
            price (float): Сумма платежа в рублях.
            description (str): Описание платежа.

        Returns:
            dict: Словарь с идентификатором платежа и URL для подтверждения.
        """
        logger.info("Создание платежа", amount=price, description=description[:50])

        idempotence_key = str(uuid.uuid4())
        payment_data = self._data_payment(price, description)

        logger.debug(
            "Данные для создания платежа",
            idempotence_key=idempotence_key,
            amount=price,
            description_length=len(description),
        )

        return await self._create_payment(price, payment_data, idempotence_key)

    async def _get_succeeded(self, payment_id: str, price: float) -> bool:
        """
        Подтверждает платеж по его идентификатору и возвращает результат.

        Args:
            payment_id (str): Идентификатор платежа.
            price (float): Сумма платежа для подтверждения.

        Returns:
            bool: True, если платеж успешно подтвержден, иначе False.
        """
        logger.info("Подтверждение платежа", payment_id=payment_id, amount=price)

        idempotence_key = str(uuid.uuid4())

        try:
            response = await asyncio.to_thread(
                Payment.capture,
                payment_id,
                {"amount": {"value": f"{price:.2f}", "currency": "RUB"}},
                idempotence_key,
            )
            status = response.status
            success = status == "succeeded"

            if success:
                logger.info(
                    "Платеж успешно подтвержден", payment_id=payment_id, amount=price
                )
            else:
                logger.warning(
                    "Платеж не подтвержден",
                    payment_id=payment_id,
                    status=response.status,
                )

            return success

        except Exception as e:
            logger.error(
                "Ошибка подтверждения платежа",
                exc_info=True,
                payment_id=payment_id,
                amount=price,
                idempotence_key=idempotence_key,
                error_type=type(e).__name__,
            )
            return False

    async def get_waiting_for_capture(self, payment_id: str) -> Optional[str]:
        """
        Проверяет статус платежа и возвращает его, если он ожидает подтверждения.

        Args:
            payment_id (str): Идентификатор платежа.

        Returns:
            str or bool: Статус платежа, если он ожидает подтверждения, иначе None.
        """
        logger.debug(
            "Проверка ожидания подтверждения платежа", extra={"payment_id": payment_id}
        )

        try:
            status = await self._get_status(payment_id)

            if status == "waiting_for_capture":
                logger.info("Платеж ожидает подтверждения", payment_id=payment_id)
                return status

            logger.debug(
                "Платеж не ожидает подтверждения",
                payment_id=payment_id,
                current_status=status,
            )
            return None

        except Exception as e:
            logger.error(
                "Ошибка проверки статуса подтверждения",
                payment_id=payment_id,
                error_type=type(e).__name__,
            )
            return None

    async def _get_status(self, payment_id: str) -> Optional[str]:
        """
        Получает статус платежа по его идентификатору.

        Args:
            payment_id (str): Идентификатор платежа.

        Returns:
            str or None: Статус платежа, если он найден, иначе None.
        """
        logger.debug("Запрос статуса платежа", payment_id=payment_id)

        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
            
            # Проверка на None перед доступом к атрибутам
            if payment is None:
                logger.warning("Платеж не найден в YooKassa", payment_id=payment_id)
                return None
            
            # Безопасное получение статуса
            status = getattr(payment, '_status', None)
            
            # Если _status недоступен, пробуем получить status напрямую
            if status is None:
                status = getattr(payment, 'status', None)

            logger.info("Статус платежа получен", payment_id=payment_id, status=status)

            return status

        except AttributeError as e:
            # Ловим AttributeError при доступе к атрибутам payment
            logger.error(
                "AttributeError при получении статуса платежа",
                exc_info=True,
                payment_id=payment_id,
                error_message=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "Ошибка получения статуса платежа",
                exc_info=True,
                extra={"payment_id": payment_id, "error_type": type(e).__name__},
            )
            return None
