import asyncpg
import punq
from punq import Container

from client import XUISession
from services.cache.service import CacheService
from dialogs.windows.getters.admin.panel import (
    AdminStatsGetter,
)
from dialogs.windows.getters.admin.key_stats import KeyStatsGetter
from dialogs.windows.getters.admin.payment_stats import PaymentStatsGetter
from dialogs.windows.getters.admin.mailing import MailingConfirmGetter
from dialogs.windows.getters.admin.keys_list import (
    AdminKeyListGetter,
    AdminKeyDetailsGetter,
)
from dialogs.windows.getters.admin.user_profile import AdminUserProfileGetter
from dialogs.windows.getters.admin.generate_key import AdminGenKeyGetter
from dialogs.windows.getters.admin.key_actions import (
    AdminKeyDeleteGetter,
    AdminKeyChangeDateGetter,
    AdminKeyChangeDateConfirmGetter,
    AdminKeyChangeTariffGetter,
    AdminKeyChangeTariffConfirmGetter,
)
from dialogs.windows.getters.admin.user_delete import AdminUserDeleteGetter
from dialogs.windows.getters.admin.dashboard import AdminDashboardGetter
from dialogs.windows.getters.admin.inactive_users import InactiveUsersGetter
from dialogs.windows.getters.admin.mass_renewal_preview import AdminMassRenewalPreviewGetter
from services.analytics.ltv_metrics import LtvMetricsService
from services.analytics.churn_metrics import ChurnMetricsService
from services.analytics.referral_metrics import ReferralMetricsService
from services.analytics.gift_metrics import GiftMetricsService
from services.analytics.payment_metrics import PaymentMetricsService
from dialogs.windows.widgets.message.admin.dashboard import AdminDashboardMessage
from dialogs.windows.widgets.keybord.admin.dashboard import AdminDashboardKeyboard
from dialogs.windows.widgets.message.admin.panel import (
    AdminMainMessage,
    AdminStatsMessage,
)
from dialogs.windows.widgets.message.admin.key_stats import KeyStatsMessage
from dialogs.windows.widgets.message.admin.payment_stats import PaymentStatsMessage
from dialogs.windows.widgets.message.admin.search import (
    SearchMainMessage,
    SearchTgIdMessage,
    SearchEmailMessage,
)
from dialogs.windows.widgets.message.admin.mailing import (
    MailingInputMessage,
    MailingConfirmMessage,
)
from dialogs.windows.widgets.message.admin.keys_list import AdminKeysListMessage
from dialogs.windows.widgets.message.admin.generate_key import (
    GenKeyInputTgIdMessage,
    GenKeyChooseInboundMessage,
    GenKeyChooseTariffMessage,
    GenKeyConfirmMessage,
    GenKeyResultMessage,
)
from dialogs.windows.widgets.message.admin.key_delete_confirm import AdminKeyDeleteConfirmMessage
from dialogs.windows.widgets.message.admin.user_delete_confirm import AdminUserDeleteConfirmMessage
from dialogs.windows.widgets.message.admin.key_change_date import (
    AdminKeyChangeDateMessage,
    AdminKeyChangeDateConfirmMessage,
)
from dialogs.windows.widgets.message.admin.key_change_tariff import (
    AdminKeyChangeTariffMessage,
    AdminKeyChangeTariffConfirmMessage,
)
from dialogs.windows.widgets.message.admin.inactive_users import (
    InactiveUsersReviewMessage,
    InactiveUsersConfirmMessage,
)
from dialogs.windows.widgets.message.admin.mass_renewal import (
    AdminMassRenewalSegmentMessage,
    AdminMassRenewalInputDaysMessage,
    AdminMassRenewalPreviewMessage,
)
from dialogs.windows.widgets.keybord.admin.panel import (
    AdminMainKeyboard,
    AdminStatsKeyboard,
)
from dialogs.windows.widgets.keybord.admin.key_stats import KeyStatsKeyboard
from dialogs.windows.widgets.keybord.admin.payment_stats import PaymentStatsKeyboard
from dialogs.windows.widgets.keybord.admin.search import (
    SearchMainKeyboard,
    SearchTgIdKeyboard,
    SearchEmailKeyboard,
)
from dialogs.windows.widgets.keybord.admin.mailing import (
    MailingInputKeyboard,
    MailingConfirmKeyboard,
)
from dialogs.windows.widgets.keybord.admin.keys_list import (
    AdminKeysListKeyboard,
    AdminKeyDetailsKeyboard,
)
from dialogs.windows.widgets.keybord.admin.generate_key import (
    GenKeyInputTgIdKeyboard,
    GenKeyChooseInboundKeyboard,
    GenKeyChooseTariffKeyboard,
    GenKeyConfirmKeyboard,
    GenKeyResultKeyboard,
)
from dialogs.windows.widgets.keybord.admin.key_delete_confirm import AdminKeyDeleteConfirmKeyboard
from dialogs.windows.widgets.keybord.admin.user_delete_confirm import AdminUserDeleteConfirmKeyboard
from dialogs.windows.widgets.keybord.admin.key_change_date import (
    AdminKeyChangeDateKeyboard,
    AdminKeyChangeDateConfirmKeyboard,
)
from dialogs.windows.widgets.keybord.admin.key_change_tariff import (
    AdminKeyChangeTariffKeyboard,
    AdminKeyChangeTariffConfirmKeyboard,
)
from dialogs.windows.widgets.keybord.admin.inactive_users import (
    InactiveUsersReviewKeyboard,
    InactiveUsersConfirmKeyboard,
)
from dialogs.windows.widgets.keybord.admin.mass_renewal_segment import (
    AdminMassRenewalSegmentKeyboard,
)
from dialogs.windows.widgets.keybord.admin.mass_renewal_input_days import (
    AdminMassRenewalInputDaysKeyboard,
)
from dialogs.windows.widgets.keybord.admin.mass_renewal_confirm import (
    AdminMassRenewalConfirmKeyboard,
)
from dialogs.windows.widgets.message.admin.user_profile import AdminUserProfileMessage
from dialogs.windows.widgets.keybord.admin.user_profile import AdminUserProfileKeyboard
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel


class AdminRegistrar(ContainerProtocol):
    """Регистратор для admin-диалогов: панель, поиск, рассылка."""

    def register_dependencies(self, container: Container) -> None:
        # ===== Panel Getters =====
        def build_admin_stats_getter():
            return AdminStatsGetter(
                model_data=container.resolve(ServiceDataModel),
            )

        def build_key_stats_getter():
            return KeyStatsGetter(
                model_data=container.resolve(ServiceDataModel),
            )

        # ===== Mailing Getter =====
        def build_mailing_confirm_getter():
            return MailingConfirmGetter()

        # ===== Keys List Getters =====
        def build_admin_key_list_getter():
            return AdminKeyListGetter(
                model_data=container.resolve(ServiceDataModel),
            )

        def build_admin_key_details_getter():
            return AdminKeyDetailsGetter()

        # ===== User Profile Getter =====
        def build_admin_user_profile_getter():
            return AdminUserProfileGetter(
                model_data=container.resolve(ServiceDataModel),
            )

        # ===== Generate Key Getter =====
        def build_admin_gen_key_getter():
            return AdminGenKeyGetter(
                cache_service=container.resolve(CacheService),
            )

        # ===== Key Actions Getters =====
        # ===== User Delete Getter =====
        def build_admin_user_delete_getter():
            return AdminUserDeleteGetter()

        # ===== Inactive Users Getter =====
        def build_inactive_users_getter():
            return InactiveUsersGetter(
                model_data=container.resolve(ServiceDataModel),
            )

        # ===== Mass Renewal Preview Getter =====
        def build_mass_renewal_preview_getter():
            return AdminMassRenewalPreviewGetter(
                cache=container.resolve(CacheService),
            )

        def build_admin_key_delete_getter():
            return AdminKeyDeleteGetter()

        def build_admin_key_change_date_getter():
            return AdminKeyChangeDateGetter()

        def build_admin_key_change_date_confirm_getter():
            return AdminKeyChangeDateConfirmGetter()

        def build_admin_key_change_tariff_getter():
            return AdminKeyChangeTariffGetter()

        def build_admin_key_change_tariff_confirm_getter():
            return AdminKeyChangeTariffConfirmGetter()

        # Register getters
        container.register(
            AdminStatsGetter,
            factory=build_admin_stats_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            KeyStatsGetter,
            factory=build_key_stats_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            MailingConfirmGetter,
            factory=build_mailing_confirm_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyListGetter,
            factory=build_admin_key_list_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyDetailsGetter,
            factory=build_admin_key_details_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminUserProfileGetter,
            factory=build_admin_user_profile_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyDeleteGetter,
            factory=build_admin_key_delete_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyChangeDateGetter,
            factory=build_admin_key_change_date_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyChangeDateConfirmGetter,
            factory=build_admin_key_change_date_confirm_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyChangeTariffGetter,
            factory=build_admin_key_change_tariff_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminKeyChangeTariffConfirmGetter,
            factory=build_admin_key_change_tariff_confirm_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminGenKeyGetter,
            factory=build_admin_gen_key_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminUserDeleteGetter,
            factory=build_admin_user_delete_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            InactiveUsersGetter,
            factory=build_inactive_users_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminMassRenewalPreviewGetter,
            factory=build_mass_renewal_preview_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            AdminDashboardGetter,
            factory=lambda: AdminDashboardGetter(
                db_pool=container.resolve(asyncpg.Pool),
                cache_service=container.resolve(CacheService),
                xui_session=container.resolve(XUISession),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            LtvMetricsService,
            factory=lambda: LtvMetricsService(
                db_pool=container.resolve(asyncpg.Pool),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            ChurnMetricsService,
            factory=lambda: ChurnMetricsService(
                db_pool=container.resolve(asyncpg.Pool),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralMetricsService,
            factory=lambda: ReferralMetricsService(
                db_pool=container.resolve(asyncpg.Pool),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            GiftMetricsService,
            factory=lambda: GiftMetricsService(
                db_pool=container.resolve(asyncpg.Pool),
            ),
            scope=punq.Scope.singleton,
        )
        container.register(
            PaymentMetricsService,
            factory=lambda: PaymentMetricsService(
                db_pool=container.resolve(asyncpg.Pool),
            ),
            scope=punq.Scope.singleton,
        )

        # ===== Payment Stats Getter =====
        def build_payment_stats_getter():
            return PaymentStatsGetter(
                payment_metrics=container.resolve(PaymentMetricsService),
            )

        container.register(
            PaymentStatsGetter,
            factory=build_payment_stats_getter,
            scope=punq.Scope.singleton,
        )

        # ===== Message Builders =====
        for message_cls in [
            AdminMainMessage,
            AdminStatsMessage,
            SearchMainMessage,
            SearchTgIdMessage,
            SearchEmailMessage,
            MailingInputMessage,
            MailingConfirmMessage,
            AdminKeysListMessage,
            AdminUserProfileMessage,
            AdminKeyDeleteConfirmMessage,
            AdminUserDeleteConfirmMessage,
            AdminKeyChangeDateMessage,
            AdminKeyChangeDateConfirmMessage,
            AdminKeyChangeTariffMessage,
            AdminKeyChangeTariffConfirmMessage,
            AdminDashboardMessage,
            GenKeyInputTgIdMessage,
            GenKeyChooseInboundMessage,
            GenKeyChooseTariffMessage,
            GenKeyConfirmMessage,
            GenKeyResultMessage,
            KeyStatsMessage,
            PaymentStatsMessage,
            InactiveUsersReviewMessage,
            InactiveUsersConfirmMessage,
            AdminMassRenewalSegmentMessage,
            AdminMassRenewalInputDaysMessage,
            AdminMassRenewalPreviewMessage,
        ]:
            container.register(
                message_cls,
                factory=lambda cls=message_cls: cls(),
                scope=punq.Scope.singleton,
            )

        # ===== Keyboard Builders =====
        for keyboard_cls in [
            AdminMainKeyboard,
            AdminStatsKeyboard,
            SearchMainKeyboard,
            SearchTgIdKeyboard,
            SearchEmailKeyboard,
            MailingInputKeyboard,
            MailingConfirmKeyboard,
            AdminKeysListKeyboard,
            AdminKeyDetailsKeyboard,
            AdminUserProfileKeyboard,
            AdminKeyDeleteConfirmKeyboard,
            AdminUserDeleteConfirmKeyboard,
            AdminKeyChangeDateKeyboard,
            AdminKeyChangeDateConfirmKeyboard,
            AdminKeyChangeTariffKeyboard,
            AdminKeyChangeTariffConfirmKeyboard,
            GenKeyInputTgIdKeyboard,
            GenKeyChooseInboundKeyboard,
            GenKeyChooseTariffKeyboard,
            GenKeyConfirmKeyboard,
            GenKeyResultKeyboard,
            AdminDashboardKeyboard,
            KeyStatsKeyboard,
            PaymentStatsKeyboard,
            InactiveUsersReviewKeyboard,
            InactiveUsersConfirmKeyboard,
            AdminMassRenewalSegmentKeyboard,
            AdminMassRenewalInputDaysKeyboard,
            AdminMassRenewalConfirmKeyboard,
        ]:
            container.register(
                keyboard_cls,
                factory=lambda cls=keyboard_cls: cls(),
                scope=punq.Scope.singleton,
            )
