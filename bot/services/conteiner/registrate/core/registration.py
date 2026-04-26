import punq
from punq import Container

from registration.registration_factory import RegistrationFactory
from registration.gift_registration import GiftRegistration
from registration.referral_registration import ReferralRegistration
from services.core.data.service import ServiceDataModel
from services.conteiner.protocol import ContainerProtocol


class RegistrationRegistrar(ContainerProtocol):
    """Регистрирует компоненты системы регистрации пользователей."""

    def register_dependencies(self, container: Container) -> None:
        def build_gift_registration():
            return GiftRegistration(service=container.resolve(ServiceDataModel))

        def build_referral_registration():
            return ReferralRegistration(service=container.resolve(ServiceDataModel))

        def build_registration_factory():
            return RegistrationFactory()

        container.register(
            GiftRegistration,
            factory=build_gift_registration,
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralRegistration,
            factory=build_referral_registration,
            scope=punq.Scope.singleton,
        )
        container.register(
            RegistrationFactory,
            factory=build_registration_factory,
            scope=punq.Scope.singleton,
        )
