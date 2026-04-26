import asyncpg
from punq import Container

from client import XUISession
from payments.pyments_webhook import HandlersPayment
from services.conteiner.protocol import ContainerProtocol
from services.core.payment.router import PaymentRouter


class HandlersPaymentRegister(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_handlers_payment():
            return HandlersPayment(
                xui_session=container.resolve(XUISession),
                db_pool=container.resolve(asyncpg.Pool),
                payment_processor=container.resolve(PaymentRouter),
            )

        container.register(HandlersPayment, factory=build_handlers_payment)
