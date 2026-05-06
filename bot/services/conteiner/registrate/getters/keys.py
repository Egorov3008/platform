import punq
from punq import Container

from dialogs.windows.getters.keys.trial_key import TrialKeyGetter
from dialogs.windows.getters.keys.key_list import KeyListGetter
from dialogs.windows.getters.keys.key_details import KeyDetailsGetter
from dialogs.windows.getters.keys.delete_key import ConfirmDeleteKeyGetter
from dialogs.windows.widgets.keybord.keys.trial_key import TrialKeyKeyboard
from dialogs.windows.widgets.keybord.keys.gift_key import GiftKeyKeyboard
from dialogs.windows.widgets.keybord.keys.key_list import KeyListKeyboard
from dialogs.windows.widgets.keybord.keys.key_details import KeyDetailsKeyboard
from dialogs.windows.widgets.keybord.keys.delete_key import DeleteKeyKeyboard
from dialogs.windows.widgets.keybord.keys.error_key import ErrorKeyKeyboard
from dialogs.windows.widgets.message.keys.trial_key import TrialKeyMessage
from dialogs.windows.widgets.message.keys.gift_key import GiftKeyMessage
from dialogs.windows.widgets.message.keys.key_list import KeyListMessage
from dialogs.windows.widgets.message.keys.key_details import KeyDetailsMessage
from dialogs.windows.widgets.message.keys.delete_key import DeleteKeyMessage
from dialogs.windows.widgets.message.keys.error_key import ErrorKeyMessage
from api.backend_client import BackendAPIClient
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel


class KeysRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        # DataGetters
        container.register(
            TrialKeyGetter,
            factory=lambda: TrialKeyGetter(),
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyListGetter,
            factory=lambda: KeyListGetter(
                backend_client=container.resolve(BackendAPIClient)
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyDetailsGetter,
            factory=lambda: KeyDetailsGetter(
                backend_client=container.resolve(BackendAPIClient)
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            ConfirmDeleteKeyGetter,
            factory=lambda: ConfirmDeleteKeyGetter(),
            scope=punq.Scope.singleton,
        )

        # KeyboardBuilders
        container.register(
            TrialKeyKeyboard,
            factory=lambda: TrialKeyKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            GiftKeyKeyboard,
            factory=lambda: GiftKeyKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyListKeyboard,
            factory=lambda: KeyListKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyDetailsKeyboard,
            factory=lambda: KeyDetailsKeyboard(
                model_data=container.resolve(ServiceDataModel),
                backend_client=container.resolve(BackendAPIClient),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            DeleteKeyKeyboard,
            factory=lambda: DeleteKeyKeyboard(
                backend_client=container.resolve(BackendAPIClient),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            ErrorKeyKeyboard,
            factory=lambda: ErrorKeyKeyboard(),
            scope=punq.Scope.singleton,
        )

        # MessageBuilders
        container.register(
            TrialKeyMessage,
            factory=lambda: TrialKeyMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            GiftKeyMessage, factory=lambda: GiftKeyMessage(), scope=punq.Scope.singleton
        )
        container.register(
            KeyListMessage, factory=lambda: KeyListMessage(), scope=punq.Scope.singleton
        )
        container.register(
            KeyDetailsMessage,
            factory=lambda: KeyDetailsMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            DeleteKeyMessage,
            factory=lambda: DeleteKeyMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            ErrorKeyMessage,
            factory=lambda: ErrorKeyMessage(),
            scope=punq.Scope.singleton,
        )
