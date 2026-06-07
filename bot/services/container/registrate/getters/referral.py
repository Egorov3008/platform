import punq
from punq import Container

from api.backend_client import BackendAPIClient
from dialogs.windows.getters.referral.main import ReferralMainGetter
from dialogs.windows.widgets.keybord.referral.main import ReferralMainKeyboard
from dialogs.windows.widgets.message.referral.main import ReferralMainMessage
from services.container.protocol import ContainerProtocol


class ReferralRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_referral_getter():
            return ReferralMainGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_referral_keyboard():
            return ReferralMainKeyboard(
                backend_client=container.resolve(BackendAPIClient),
            )

        container.register(
            ReferralMainGetter,
            factory=build_referral_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralMainMessage,
            factory=lambda: ReferralMainMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralMainKeyboard,
            factory=build_referral_keyboard,
            scope=punq.Scope.singleton,
        )
