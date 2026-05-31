import punq
from punq import Container

from services.cache.loader import LoadingService
from services.conteiner.protocol import ContainerProtocol


class CoreServiceRegistrar(ContainerProtocol):
    """Регистратор основных сервисов (legacy DI wiring)."""

    def register_dependencies(self, container: Container) -> None:
        def build_loading_service():
            return LoadingService()

        container.register(
            LoadingService, factory=build_loading_service, scope=punq.Scope.singleton
        )
