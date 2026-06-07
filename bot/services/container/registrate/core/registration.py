import punq
from punq import Container

from api.backend_client import BackendAPIClient
from registration.registration_factory import RegistrationFactory
from registration.gift_registration import GiftRegistration
from registration.referral_registration import ReferralRegistration
from services.container.protocol import ContainerProtocol


class RegistrationRegistrar(ContainerProtocol):
    """Регистрирует компоненты системы регистрации пользователей."""

    def register_dependencies(self, container: Container) -> None:
        def build_gift_registration():
            return GiftRegistration(backend=container.resolve(BackendAPIClient))

        def build_referral_registration():
            return ReferralRegistration(backend=container.resolve(BackendAPIClient))

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
