import punq
from punq import Container

from api.backend_client import BackendAPIClient
from services.conteiner.protocol import ContainerProtocol
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario


class ScenarioKeyRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_create_first_key():
            return CreateFerstKeyScenario(
                backend_client=container.resolve(BackendAPIClient),
            )

        container.register(
            CreateFerstKeyScenario,
            factory=build_create_first_key,
            scope=punq.Scope.transient,
        )
