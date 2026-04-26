import punq
from punq import Container

from dialogs.windows.getters.profile.main import UserDataGetter
from dialogs.windows.widgets.keybord.profile.main import UserKeyboardBuilder
from dialogs.windows.widgets.keybord.profile.welcome import WelcomeKeyboard
from dialogs.windows.widgets.message.profile.main import UserMessageBuilder
from dialogs.windows.widgets.message.profile.welcom import WelcomeMessage
from api.backend_client import BackendAPIClient
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel
from services.core.gift.repositories.checker import CheckerGiftLink
from services.core.user.utils.checked_admin import CheckedUser
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario


class ProfileRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_user_data_getter():
            return UserDataGetter(
                backend_client=container.resolve(BackendAPIClient),
                checker_link=container.resolve(CheckerGiftLink),
                checked_user=container.resolve(CheckedUser),
            )

        def build_welcome_keyboard():
            return WelcomeKeyboard()

        def build_user_keyboard():
            return UserKeyboardBuilder(
                model_service=container.resolve(ServiceDataModel),
                create_trial_key=container.resolve(CreateFerstKeyScenario),
            )

        container.register(
            UserDataGetter, factory=build_user_data_getter, scope=punq.Scope.singleton
        )
        container.register(
            WelcomeKeyboard, factory=build_welcome_keyboard, scope=punq.Scope.singleton
        )
        container.register(
            UserKeyboardBuilder, factory=build_user_keyboard, scope=punq.Scope.singleton
        )
        container.register(
            WelcomeMessage, factory=lambda: WelcomeMessage(), scope=punq.Scope.singleton
        )
        container.register(
            UserMessageBuilder,
            factory=lambda: UserMessageBuilder(),
            scope=punq.Scope.singleton,
        )
