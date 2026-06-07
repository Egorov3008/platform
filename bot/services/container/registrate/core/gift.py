import punq
from punq import Container

from api.backend_client import BackendAPIClient
from services.container.protocol import ContainerProtocol
from services.core.gift.repositories.checker import CheckerGiftLink


class GiftServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_checking_gift():
            return CheckerGiftLink(backend=container.resolve(BackendAPIClient))

        container.register(
            CheckerGiftLink, factory=build_checking_gift, scope=punq.Scope.singleton
        )
