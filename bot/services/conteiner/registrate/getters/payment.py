import punq
from punq import Container

from dialogs.windows.getters.payment.form_pay import FormPaymentGetter
from dialogs.windows.getters.payment.setting_payment import SettingsPayment
from dialogs.windows.widgets.general import CancelKeyboard
from dialogs.windows.widgets.keybord.payment.form_pay import PaymentFormKeyboard
from dialogs.windows.widgets.keybord.payment.setting_payment import (
    SettingPaymentKeyboard,
)
from dialogs.windows.widgets.keybord.payment.view_tariff import TariffSelectBuilder
from dialogs.windows.widgets.message.payment.form_pay import InstructionsPaymentMessage
from dialogs.windows.widgets.message.payment.setting_pay import (
    SettingsPayment as SettingsPaymentMessage,
)
from api.backend_client import BackendAPIClient
from services.conteiner.protocol import ContainerProtocol
from services.core.price.service import PriceService


class PaymentRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_settings_payment():
            return SettingsPayment(
                price_service=container.resolve(PriceService),
                backend=container.resolve(BackendAPIClient),
            )

        def build_form_payment_getter():
            return FormPaymentGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_tariff_select_builder():
            return TariffSelectBuilder()

        def builder_payment_form_keybord():
            return PaymentFormKeyboard(
                backend_client=container.resolve(BackendAPIClient),
            )

        container.register(
            SettingsPayment, factory=build_settings_payment, scope=punq.Scope.singleton
        )
        container.register(
            FormPaymentGetter,
            factory=build_form_payment_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            TariffSelectBuilder,
            factory=build_tariff_select_builder,
            scope=punq.Scope.singleton,
        )
        container.register(
            PaymentFormKeyboard,
            factory=builder_payment_form_keybord,
            scope=punq.Scope.singleton,
        )
        container.register(
            SettingPaymentKeyboard,
            factory=lambda: SettingPaymentKeyboard(),
            scope=punq.Scope.singleton,
        )
        container.register(
            InstructionsPaymentMessage,
            factory=lambda: InstructionsPaymentMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            SettingsPaymentMessage,
            factory=lambda: SettingsPaymentMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            CancelKeyboard, factory=lambda: CancelKeyboard(), scope=punq.Scope.singleton
        )
