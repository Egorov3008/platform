from typing import List

from punq import Container

from dialogs.windows.window_factory import WindowFactory
from services.container.app import get_container
from states import (
    MainMenu,
    Tariff,
    GiftStates,
    PaymentState,
    KeysInit,
    Instruction,
    UsageRules,
    AdminManager,
    AdminSearchManagementSG,
    AdminMassMailing,
    AdminKeyDeleteSG,
    AdminKeyChangeDateSG,
    AdminKeyChangeTariffSG,
    AdminGenerateKeySG,
    AdminUserDeleteSG,
    AdminUserCleanupSG,
    AdminMassRenewal,
    ReferralSistem,
)
from .getters.gift import MainGetter
from .getters.keys import (
    TrialKeyGetter,
    KeyListGetter,
    KeyDetailsGetter,
    ConfirmDeleteKeyGetter,
)
from .getters.payment.form_pay import FormPaymentGetter
from .getters.payment.setting_payment import SettingsPayment as SettingsPaymentGetter
from .getters.profile import UserDataGetter
from .getters.tariff import TariffPreviewGetter
from .getters.admin import (
    AdminStatsGetter,
    MailingConfirmGetter,
    AdminKeyListGetter,
    AdminKeyDetailsGetter,
    AdminGenKeyGetter,
    AdminUserDeleteGetter,
    AdminDashboardGetter,
    KeyStatsGetter,
    PaymentStatsGetter,
    InactiveUsersGetter,
    AdminMassRenewalPreviewGetter,
)
from .getters.admin.user_profile import AdminUserProfileGetter
from .getters.admin.key_actions import (
    AdminKeyDeleteGetter,
    AdminKeyChangeDateGetter,
    AdminKeyChangeDateConfirmGetter,
    AdminKeyChangeTariffGetter,
    AdminKeyChangeTariffConfirmGetter,
)
from .widgets import CancelKeyboard
from .widgets.keybord.gift import GiftMainKeyboard
from .widgets.keybord.keys import (
    TrialKeyKeyboard,
    GiftKeyKeyboard,
    KeyListKeyboard,
    KeyDetailsKeyboard,
    DeleteKeyKeyboard,
)
from .widgets.keybord.keys.error_key import ErrorKeyKeyboard
from .widgets.keybord.payment import TariffSelectBuilder
from .widgets.keybord.payment.form_pay import PaymentFormKeyboard
from .widgets.keybord.payment.setting_payment import SettingPaymentKeyboard
from .widgets.keybord.profile import UserKeyboardBuilder, WelcomeKeyboard
from .widgets.keybord.profile.min_main import MinMainKeyboard
from .widgets.keybord.admin.keys_list import AdminKeysListKeyboard, AdminKeyDetailsKeyboard
from .widgets.keybord.admin.key_delete_confirm import AdminKeyDeleteConfirmKeyboard
from .widgets.keybord.admin.key_change_date import (
    AdminKeyChangeDateKeyboard,
    AdminKeyChangeDateConfirmKeyboard,
)
from .widgets.keybord.admin.key_change_tariff import (
    AdminKeyChangeTariffKeyboard,
    AdminKeyChangeTariffConfirmKeyboard,
)
from .widgets.message.gift import GiftMainMessage
from .widgets.message.keys import (
    TrialKeyMessage,
    GiftKeyMessage,
    KeyListMessage,
    KeyDetailsMessage,
    DeleteKeyMessage,
)
from .widgets.message.keys.error_key import ErrorKeyMessage
from .widgets.message.payment.form_pay import InstructionsPaymentMessage
from .widgets.message.payment.setting_pay import (
    SettingsPayment as SettingsPaymentMessage,
)
from .widgets.message.profile import UserMessageBuilder, WelcomeMessage
from .widgets.message.profile.min_main import MinMainMessage
from .widgets.message.instruction.choosing_device import InstructionChoosingMessage
from .widgets.message.instruction.device_step import InstructionDeviceMessage
from .widgets.message.tariff import TariffPreviewMessage
from .widgets.message.admin import (
    AdminMainMessage,
    AdminStatsMessage,
    SearchMainMessage,
    SearchTgIdMessage,
    SearchEmailMessage,
    MailingInputMessage,
    MailingConfirmMessage,
    AdminKeysListMessage,
    GenKeyInputTgIdMessage,
    GenKeyChooseTariffMessage,
    GenKeyConfirmMessage,
    GenKeyResultMessage,
    AdminDashboardMessage,
    KeyStatsMessage,
    PaymentStatsMessage,
    InactiveUsersReviewMessage,
    InactiveUsersConfirmMessage,
    AdminMassRenewalSegmentMessage,
    AdminMassRenewalInputDaysMessage,
    AdminMassRenewalPreviewMessage,
)
from .widgets.message.admin.user_profile import AdminUserProfileMessage
from .widgets.message.admin.key_delete_confirm import AdminKeyDeleteConfirmMessage
from .widgets.message.admin.user_delete_confirm import AdminUserDeleteConfirmMessage
from .widgets.message.admin.key_change_date import (
    AdminKeyChangeDateMessage,
    AdminKeyChangeDateConfirmMessage,
)
from .widgets.message.admin.key_change_tariff import (
    AdminKeyChangeTariffMessage,
    AdminKeyChangeTariffConfirmMessage,
)
from .widgets.keybord.instruction.choosing_device import InstructionChoosingKeyboard
from .widgets.keybord.instruction.android import AndroidDeviceKeyboard
from .widgets.keybord.instruction.iphone import IphoneDeviceKeyboard
from .widgets.keybord.instruction.windows_device import WindowsDeviceKeyboard
from .widgets.keybord.instruction.linux import LinuxDeviceKeyboard
from .widgets.message.usage_rules.main import (
    UsageRulesMainMessage,
    UsageRulesPageMessage,
)
from .widgets.keybord.usage_rules.main import (
    UsageRulesMainKeyboard,
    UsageRulesPageKeyboard,
)
from .widgets.keybord.admin import (
    AdminMainKeyboard,
    AdminStatsKeyboard,
    SearchMainKeyboard,
    SearchTgIdKeyboard,
    SearchEmailKeyboard,
    MailingInputKeyboard,
    MailingConfirmKeyboard,
    GenKeyInputTgIdKeyboard,
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
)
from .widgets.keybord.admin.user_profile import AdminUserProfileKeyboard
from .widgets.keybord.admin.user_delete_confirm import AdminUserDeleteConfirmKeyboard
from .getters.referral import ReferralMainGetter
from .widgets.message.referral import ReferralMainMessage
from .widgets.keybord.referral import ReferralMainKeyboard

# профиль меню

profile_windows = [
    {
        "state": MainMenu.welcome,
        "message_cls": WelcomeMessage,
        "keyboard_cls": WelcomeKeyboard,
        "getter_cls": None,
    },
    {
        "state": MainMenu.main,
        "message_cls": UserMessageBuilder,
        "keyboard_cls": UserKeyboardBuilder,
        "getter_cls": UserDataGetter,
    },
    {
        "state": MainMenu.min_main,
        "message_cls": MinMainMessage,
        "keyboard_cls": MinMainKeyboard,
        "getter_cls": UserDataGetter,
    },
]

# Тарифы

tariff_windows = [
    {
        "state": Tariff.preview,
        "message_cls": TariffPreviewMessage,
        "keyboard_cls": CancelKeyboard,
        "getter_cls": TariffPreviewGetter,
    },
]

# Состояния подарочных ключей

gift_windows = [
    {
        "state": GiftStates.main,
        "message_cls": GiftMainMessage,
        "keyboard_cls": GiftMainKeyboard,
        "getter_cls": MainGetter,
    },
]
# Оплата
payment_windows = [
    {
        "state": PaymentState.view_tariff,
        "message_cls": TariffPreviewMessage,
        "keyboard_cls": TariffSelectBuilder,
        "getter_cls": TariffPreviewGetter,
    },
    {
        "state": PaymentState.setting_pay,
        "message_cls": SettingsPaymentMessage,
        "keyboard_cls": SettingPaymentKeyboard,
        "getter_cls": SettingsPaymentGetter,
    },
    {
        "state": PaymentState.form_pay,
        "message_cls": InstructionsPaymentMessage,
        "keyboard_cls": PaymentFormKeyboard,
        "getter_cls": FormPaymentGetter,
    },
]
# Ключи

keys_windows = [
    {
        "state": KeysInit.create_trial,
        "message_cls": TrialKeyMessage,
        "keyboard_cls": TrialKeyKeyboard,
        "getter_cls": TrialKeyGetter,
    },
    {
        "state": KeysInit.create_gift_key,
        "message_cls": GiftKeyMessage,
        "keyboard_cls": GiftKeyKeyboard,
        "getter_cls": TrialKeyGetter,
    },
    {
        "state": KeysInit.list,
        "message_cls": KeyListMessage,
        "keyboard_cls": KeyListKeyboard,
        "getter_cls": KeyListGetter,
    },
    {
        "state": KeysInit.key,
        "message_cls": KeyDetailsMessage,
        "keyboard_cls": KeyDetailsKeyboard,
        "getter_cls": KeyDetailsGetter,
    },
    {
        "state": KeysInit.confirmation_delete_key,
        "message_cls": DeleteKeyMessage,
        "keyboard_cls": DeleteKeyKeyboard,
        "getter_cls": ConfirmDeleteKeyGetter,
    },
    {
        "state": KeysInit.error,
        "message_cls": ErrorKeyMessage,
        "keyboard_cls": ErrorKeyKeyboard,
        "getter_cls": None,
    },
]

# Окна регистрации (удалены в пользу автоматической регистрации)

register_windows = []

# Окна инструкции

instruction_windows = [
    {
        "state": Instruction.choosing_device,
        "message_cls": InstructionChoosingMessage,
        "keyboard_cls": InstructionChoosingKeyboard,
        "getter_cls": None,
    },
    {
        "state": Instruction.android,
        "message_cls": InstructionDeviceMessage,
        "keyboard_cls": AndroidDeviceKeyboard,
        "getter_cls": None,
    },
    {
        "state": Instruction.iphone,
        "message_cls": InstructionDeviceMessage,
        "keyboard_cls": IphoneDeviceKeyboard,
        "getter_cls": None,
    },
    {
        "state": Instruction.windows,
        "message_cls": InstructionDeviceMessage,
        "keyboard_cls": WindowsDeviceKeyboard,
        "getter_cls": None,
    },
    {
        "state": Instruction.linux,
        "message_cls": InstructionDeviceMessage,
        "keyboard_cls": LinuxDeviceKeyboard,
        "getter_cls": None,
    },
]

# Правила использования

usage_rules_windows = [
    {
        "state": UsageRules.main,
        "message_cls": UsageRulesMainMessage,
        "keyboard_cls": UsageRulesMainKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page1,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page2,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page3,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page4,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page5,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page6,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page7,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page8,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
    {
        "state": UsageRules.page9,
        "message_cls": UsageRulesPageMessage,
        "keyboard_cls": UsageRulesPageKeyboard,
        "getter_cls": None,
    },
]

# Admin диалоги: панель администратора

admin_panel_windows = [
    {
        "state": AdminManager.main,
        "message_cls": AdminMainMessage,
        "keyboard_cls": AdminMainKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminManager.static_user,
        "message_cls": AdminStatsMessage,
        "keyboard_cls": AdminStatsKeyboard,
        "getter_cls": AdminStatsGetter,
    },
    {
        "state": AdminManager.key_stats,
        "message_cls": KeyStatsMessage,
        "keyboard_cls": KeyStatsKeyboard,
        "getter_cls": KeyStatsGetter,
    },
    {
        "state": AdminManager.payment_stats,
        "message_cls": PaymentStatsMessage,
        "keyboard_cls": PaymentStatsKeyboard,
        "getter_cls": PaymentStatsGetter,
    },
    {
        "state": AdminManager.key_list,
        "message_cls": AdminKeysListMessage,
        "keyboard_cls": AdminKeysListKeyboard,
        "getter_cls": AdminKeyListGetter,
    },
    {
        "state": AdminManager.key_details,
        "message_cls": KeyDetailsMessage,
        "keyboard_cls": AdminKeyDetailsKeyboard,
        "getter_cls": AdminKeyDetailsGetter,
    },
    {
        "state": AdminManager.dashboard,
        "message_cls": AdminDashboardMessage,
        "keyboard_cls": AdminDashboardKeyboard,
        "getter_cls": AdminDashboardGetter,
    },
]

# Admin диалоги: поиск

admin_search_windows = [
    {
        "state": AdminSearchManagementSG.main,
        "message_cls": SearchMainMessage,
        "keyboard_cls": SearchMainKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminSearchManagementSG.search_tg_id,
        "message_cls": SearchTgIdMessage,
        "keyboard_cls": SearchTgIdKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminSearchManagementSG.search_email,
        "message_cls": SearchEmailMessage,
        "keyboard_cls": SearchEmailKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminSearchManagementSG.profile_user,
        "message_cls": AdminUserProfileMessage,
        "keyboard_cls": AdminUserProfileKeyboard,
        "getter_cls": AdminUserProfileGetter,
    },
]

# Admin диалоги: массовая рассылка

admin_mailing_windows = [
    {
        "state": AdminMassMailing.receiving_message,
        "message_cls": MailingInputMessage,
        "keyboard_cls": MailingInputKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminMassMailing.confirmation,
        "message_cls": MailingConfirmMessage,
        "keyboard_cls": MailingConfirmKeyboard,
        "getter_cls": MailingConfirmGetter,
    },
]

# Admin диалоги: профиль пользователя (перемещено в admin_search_windows)

admin_user_profile_windows = []

# Admin диалоги: регистрация новых пользователей

# Admin диалоги: удаление ключа

admin_key_delete_windows = [
    {
        "state": AdminKeyDeleteSG.confirm,
        "message_cls": AdminKeyDeleteConfirmMessage,
        "keyboard_cls": AdminKeyDeleteConfirmKeyboard,
        "getter_cls": AdminKeyDeleteGetter,
    },
]

# Admin диалоги: удаление пользователя

admin_user_delete_windows = [
    {
        "state": AdminUserDeleteSG.confirm,
        "message_cls": AdminUserDeleteConfirmMessage,
        "keyboard_cls": AdminUserDeleteConfirmKeyboard,
        "getter_cls": AdminUserDeleteGetter,
    },
]

# Admin диалоги: изменение даты истечения ключа

admin_key_change_date_windows = [
    {
        "state": AdminKeyChangeDateSG.pick_date,
        "message_cls": AdminKeyChangeDateMessage,
        "keyboard_cls": AdminKeyChangeDateKeyboard,
        "getter_cls": AdminKeyChangeDateGetter,
    },
    {
        "state": AdminKeyChangeDateSG.confirm,
        "message_cls": AdminKeyChangeDateConfirmMessage,
        "keyboard_cls": AdminKeyChangeDateConfirmKeyboard,
        "getter_cls": AdminKeyChangeDateConfirmGetter,
    },
]

# Admin диалоги: изменение тарифа ключа

admin_key_change_tariff_windows = [
    {
        "state": AdminKeyChangeTariffSG.pick_tariff,
        "message_cls": AdminKeyChangeTariffMessage,
        "keyboard_cls": AdminKeyChangeTariffKeyboard,
        "getter_cls": AdminKeyChangeTariffGetter,
    },
    {
        "state": AdminKeyChangeTariffSG.confirm,
        "message_cls": AdminKeyChangeTariffConfirmMessage,
        "keyboard_cls": AdminKeyChangeTariffConfirmKeyboard,
        "getter_cls": AdminKeyChangeTariffConfirmGetter,
    },
]

# Admin диалоги: генерация ключа

admin_generate_key_windows = [
    {
        "state": AdminGenerateKeySG.input_tg_id,
        "message_cls": GenKeyInputTgIdMessage,
        "keyboard_cls": GenKeyInputTgIdKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminGenerateKeySG.choosing_tariff,
        "message_cls": GenKeyChooseTariffMessage,
        "keyboard_cls": GenKeyChooseTariffKeyboard,
        "getter_cls": AdminGenKeyGetter,
    },
    {
        "state": AdminGenerateKeySG.confirm_generate,
        "message_cls": GenKeyConfirmMessage,
        "keyboard_cls": GenKeyConfirmKeyboard,
        "getter_cls": AdminGenKeyGetter,
    },
    {
        "state": AdminGenerateKeySG.result,
        "message_cls": GenKeyResultMessage,
        "keyboard_cls": GenKeyResultKeyboard,
        "getter_cls": AdminGenKeyGetter,
    },
]

referral_windows = [
    {
        "state": ReferralSistem.main,
        "message_cls": ReferralMainMessage,
        "keyboard_cls": ReferralMainKeyboard,
        "getter_cls": ReferralMainGetter,
    },
]

admin_user_cleanup_windows = [
    {
        "state": AdminUserCleanupSG.review,
        "message_cls": InactiveUsersReviewMessage,
        "keyboard_cls": InactiveUsersReviewKeyboard,
        "getter_cls": InactiveUsersGetter,
    },
    {
        "state": AdminUserCleanupSG.confirm,
        "message_cls": InactiveUsersConfirmMessage,
        "keyboard_cls": InactiveUsersConfirmKeyboard,
        "getter_cls": InactiveUsersGetter,
    },
]

# Admin диалоги: массовое продление ключей

admin_mass_renewal_windows = [
    {
        "state": AdminMassRenewal.select_segment,
        "message_cls": AdminMassRenewalSegmentMessage,
        "keyboard_cls": AdminMassRenewalSegmentKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminMassRenewal.input_days,
        "message_cls": AdminMassRenewalInputDaysMessage,
        "keyboard_cls": AdminMassRenewalInputDaysKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminMassRenewal.preview,
        "message_cls": AdminMassRenewalPreviewMessage,
        "keyboard_cls": AdminMassRenewalConfirmKeyboard,
        "getter_cls": AdminMassRenewalPreviewGetter,
    },
]

ALL_WINDOW_CONFIGS = (
    profile_windows
    + tariff_windows
    + gift_windows
    + referral_windows
    + payment_windows
    + keys_windows
    + register_windows
    + instruction_windows
    + usage_rules_windows
    + admin_panel_windows
    + admin_search_windows
    + admin_mailing_windows
    + admin_user_profile_windows
    + admin_key_delete_windows
    + admin_user_delete_windows
    + admin_key_change_date_windows
    + admin_key_change_tariff_windows
    + admin_generate_key_windows
    + admin_user_cleanup_windows
    + admin_mass_renewal_windows
)


async def setup(window_data: List[dict]):
    container: Container = await get_container()
    factory_windows = WindowFactory(container)
    return factory_windows.form_state_group(window_data)
