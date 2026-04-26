import punq
from punq import Container

from dialogs.windows.widgets.keybord.usage_rules.main import (
    UsageRulesMainKeyboard,
    UsageRulesPageKeyboard,
)
from dialogs.windows.widgets.message.usage_rules.main import (
    UsageRulesMainMessage,
    UsageRulesPageMessage,
)
from services.conteiner.protocol import ContainerProtocol


class UsageRulesRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        # KeyboardBuilders
        container.register(
            UsageRulesMainKeyboard,
            factory=lambda: UsageRulesMainKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            UsageRulesPageKeyboard,
            factory=lambda: UsageRulesPageKeyboard(),
            scope=punq.Scope.singleton,
        )

        # MessageBuilders
        container.register(
            UsageRulesMainMessage,
            factory=lambda: UsageRulesMainMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            UsageRulesPageMessage,
            factory=lambda: UsageRulesPageMessage(),
            scope=punq.Scope.singleton,
        )
