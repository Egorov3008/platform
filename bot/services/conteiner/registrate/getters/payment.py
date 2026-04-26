import asyncpg
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
from payments.pay_config import YooKassService
from services.cache import CacheService
from services.conteiner.protocol import ContainerProtocol
from services.core.price.service import PriceService
from services.core.data.service import ServiceDataModel
from services.core.payment.processor import PaymentProcessor
from services.core.payment.router import PaymentRouter
from services.core.payment.creation_service import KeyCreationService
from services.core.payment.renewal_service import KeyRenewalService
from services.core.keys.utils.create_key import CreateKey
from services.core.keys.utils.renewal import KeyRenewal
from services.core.referral.bonus_service import ReferralBonusService
from services.core.referral.link_generator import ReferralLinkGenerator


class PaymentRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_yookassa_service():
            return YooKassService()

        def build_settings_payment():
            return SettingsPayment(
                price_service=container.resolve(PriceService),
                model_data=container.resolve(ServiceDataModel),
            )

        def build_form_payment_getter():
            return FormPaymentGetter(
                service=container.resolve(YooKassService),
                model_service=container.resolve(ServiceDataModel),
                conn=container.resolve(asyncpg.Pool),
            )

        def build_tariff_select_builder():
            return TariffSelectBuilder(
                model_service=container.resolve(ServiceDataModel),
                cache_service=container.resolve(CacheService),
            )

        def build_payment_processor():
            return PaymentProcessor(
                conn=container.resolve(asyncpg.Pool),
                model_service=container.resolve(ServiceDataModel),
                cache=container.resolve(CacheService),
            )

        def build_key_creation_service():
            return KeyCreationService(
                processor=container.resolve(PaymentProcessor),
                create_key=container.resolve(CreateKey),
            )

        def build_key_renewal_service():
            return KeyRenewalService(
                processor=container.resolve(PaymentProcessor),
                key_manager=container.resolve(KeyRenewal),
            )

        def build_bonus_service():
            return ReferralBonusService(
                model_data=container.resolve(ServiceDataModel),
            )

        def build_link_generator():
            return ReferralLinkGenerator(
                model_data=container.resolve(ServiceDataModel),
            )

        def build_payment_router():
            return PaymentRouter(
                processor=container.resolve(PaymentProcessor),
                creation_service=container.resolve(KeyCreationService),
                renewal_service=container.resolve(KeyRenewalService),
                bonus_service=container.resolve(ReferralBonusService),
            )

        def builder_payment_form_keybord():
            return PaymentFormKeyboard(
                payment_processor=container.resolve(PaymentRouter),
                model_service=container.resolve(ServiceDataModel),
            )

        # Регистрируем PaymentProcessor первым, чтобы сервисы могли его использовать
        container.register(
            PaymentProcessor,
            factory=build_payment_processor,
            scope=punq.Scope.singleton,
        )

        # Регистрируем сервисы создания и продления ключей
        container.register(
            KeyCreationService,
            factory=build_key_creation_service,
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyRenewalService,
            factory=build_key_renewal_service,
            scope=punq.Scope.singleton,
        )

        # Регистрируем остальное
        container.register(
            YooKassService, factory=build_yookassa_service, scope=punq.Scope.singleton
        )
        container.register(
            ReferralBonusService,
            factory=build_bonus_service,
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralLinkGenerator,
            factory=build_link_generator,
            scope=punq.Scope.singleton,
        )
        container.register(
            PaymentRouter, factory=build_payment_router, scope=punq.Scope.singleton
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
