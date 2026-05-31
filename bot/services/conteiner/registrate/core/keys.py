from services.conteiner.protocol import ContainerProtocol
from punq import Container


class KeyServiceRegistrar(ContainerProtocol):
    """No-op: key services moved to backend API."""

    def register_dependencies(self, container: Container) -> None:
        pass
