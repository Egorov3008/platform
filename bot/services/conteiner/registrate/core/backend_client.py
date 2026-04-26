import punq
from punq import Container

from api.backend_client import BackendAPIClient
from config import BACKEND_URL, BOT_SECRET_KEY
from services.conteiner.protocol import ContainerProtocol


class BackendClientRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_backend_client() -> BackendAPIClient:
            return BackendAPIClient(
                base_url=BACKEND_URL,
                bot_secret=BOT_SECRET_KEY,
            )

        container.register(
            BackendAPIClient,
            factory=build_backend_client,
            scope=punq.Scope.singleton,
        )
