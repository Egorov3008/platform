import punq
from punq import Container

from api.backend_client import BackendAPIClient
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


class AdminRegistrar(ContainerProtocol):
    """Регистратор для admin-диалогов: панель, поиск, рассылка."""

    def register_dependencies(self, container: Container) -> None:
        # ===== Panel Getters =====
        def build_admin_stats_getter():
            return AdminStatsGetter(
                backend=container.resolve(BackendAPIClient),
            )

        def build_key_stats_getter():
            return KeyStatsGetter(
                backend=container.resolve(BackendAPIClient),
            )

        # ===== Mailing Getter =====
        def build_mailing_confirm_getter():
            return MailingConfirmGetter()

        # ===== Keys List Getters =====
        def build_admin_key_list_getter():
            return AdminKeyListGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_admin_key_details_getter():
            return AdminKeyDetailsGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        # ===== User Profile Getter =====
        def build_admin_user_profile_getter():
            return AdminUserProfileGetter(
                backend=container.resolve(BackendAPIClient),
            )

        # ===== Generate Key Getter =====
        def build_admin_gen_key_getter():
            return AdminGenKeyGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        # ===== Key Actions Getters =====
        # ===== User Delete Getter =====
        def build_admin_user_delete_getter():
            return AdminUserDeleteGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        # ===== Inactive Users Getter =====
        def build_inactive_users_getter():
            return InactiveUsersGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        # ===== Mass Renewal Preview Getter =====
        def build_mass_renewal_preview_getter():
            return AdminMassRenewalPreviewGetter(
                backend=container.resolve(BackendAPIClient),
            )

        def build_admin_key_delete_getter():
            return AdminKeyDeleteGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_admin_key_change_date_getter():
            return AdminKeyChangeDateGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_admin_key_change_date_confirm_getter():
            return AdminKeyChangeDateConfirmGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_admin_key_change_tariff_getter():
            return AdminKeyChangeTariffGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

        def build_admin_key_change_tariff_confirm_getter():
            return AdminKeyChangeTariffConfirmGetter(
                backend_client=container.resolve(BackendAPIClient),
            )

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
                backend=container.resolve(BackendAPIClient),
            ),
            scope=punq.Scope.singleton,
        )

        # ===== Payment Stats Getter =====
        def build_payment_stats_getter():
            return PaymentStatsGetter(
                backend=container.resolve(BackendAPIClient),
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
