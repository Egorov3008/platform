import punq
from punq import Container

from dialogs.windows.getters.register.captcha import CaptchaGetter
from dialogs.windows.widgets.keybord.profile.min_main import MinMainKeyboard
from dialogs.windows.widgets.keybord.register.captcha import CaptchaKeyboard
from dialogs.windows.widgets.message.profile.min_main import MinMainMessage
from dialogs.windows.widgets.message.register.captcha import CaptchaMessage
from services.container.protocol import ContainerProtocol


class RegisterRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        container.register(
            CaptchaGetter,
            factory=lambda: CaptchaGetter(),
            scope=punq.Scope.singleton,
        )
        container.register(
            CaptchaKeyboard,
            factory=lambda: CaptchaKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            CaptchaMessage,
            factory=lambda: CaptchaMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            MinMainKeyboard,
            factory=lambda: MinMainKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            MinMainMessage,
            factory=lambda: MinMainMessage(),
            scope=punq.Scope.singleton,
        )
