from typing import Protocol
from punq import Container


class ContainerProtocol(Protocol):
    def register_dependencies(self, container: Container) -> None: ...
