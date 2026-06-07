import punq
from punq import Container

from services.container.protocol import ContainerProtocol
from services.core.user.utils.checked_admin import CheckedUser


class UserServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        container.register(CheckedUser, scope=punq.Scope.singleton)
