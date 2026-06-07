import punq
from punq import Container

from dialogs.windows.widgets.keybord.instruction.android import AndroidDeviceKeyboard
from dialogs.windows.widgets.keybord.instruction.choosing_device import (
    InstructionChoosingKeyboard,
)
from dialogs.windows.widgets.keybord.instruction.iphone import IphoneDeviceKeyboard
from dialogs.windows.widgets.keybord.instruction.linux import LinuxDeviceKeyboard
from dialogs.windows.widgets.keybord.instruction.windows_device import (
    WindowsDeviceKeyboard,
)
from dialogs.windows.widgets.message.instruction.choosing_device import (
    InstructionChoosingMessage,
)
from dialogs.windows.widgets.message.instruction.device_step import (
    InstructionDeviceMessage,
)
from api.backend_client import BackendAPIClient
from services.container.protocol import ContainerProtocol
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario


class InstructionRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_device_keyboard(cls):
            return cls(
                backend_client=container.resolve(BackendAPIClient),
                create_trial_key=container.resolve(CreateFerstKeyScenario),
            )

        # KeyboardBuilders
        container.register(
            InstructionChoosingKeyboard,
            factory=lambda: InstructionChoosingKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            AndroidDeviceKeyboard,
            factory=lambda: build_device_keyboard(AndroidDeviceKeyboard),
            scope=punq.Scope.singleton,
        )
        container.register(
            IphoneDeviceKeyboard,
            factory=lambda: build_device_keyboard(IphoneDeviceKeyboard),
            scope=punq.Scope.singleton,
        )
        container.register(
            WindowsDeviceKeyboard,
            factory=lambda: build_device_keyboard(WindowsDeviceKeyboard),
            scope=punq.Scope.singleton,
        )
        container.register(
            LinuxDeviceKeyboard,
            factory=lambda: build_device_keyboard(LinuxDeviceKeyboard),
            scope=punq.Scope.singleton,
        )

        # MessageBuilders
        container.register(
            InstructionChoosingMessage,
            factory=lambda: InstructionChoosingMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            InstructionDeviceMessage,
            factory=lambda: InstructionDeviceMessage(),
            scope=punq.Scope.singleton,
        )
