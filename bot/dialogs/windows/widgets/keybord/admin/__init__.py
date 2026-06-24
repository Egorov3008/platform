from .panel import AdminMainKeyboard, AdminStatsKeyboard
from .search import SearchMainKeyboard, SearchTgIdKeyboard, SearchEmailKeyboard
from .mailing import MailingInputKeyboard, MailingConfirmKeyboard
from .keys_list import AdminKeysListKeyboard, AdminKeyDetailsKeyboard
from .generate_key import (
    GenKeyInputTgIdKeyboard,
    GenKeyChooseTariffKeyboard,
    GenKeyConfirmKeyboard,
    GenKeyResultKeyboard,
)
from .dashboard import AdminDashboardKeyboard
from .key_stats import KeyStatsKeyboard
from .payment_stats import PaymentStatsKeyboard
from .inactive_users import InactiveUsersReviewKeyboard, InactiveUsersConfirmKeyboard
from .mass_renewal_segment import AdminMassRenewalSegmentKeyboard
from .mass_renewal_input_days import AdminMassRenewalInputDaysKeyboard
from .mass_renewal_confirm import AdminMassRenewalConfirmKeyboard

__all__ = [
    "AdminMainKeyboard",
    "AdminStatsKeyboard",
    "SearchMainKeyboard",
    "SearchTgIdKeyboard",
    "SearchEmailKeyboard",
    "MailingInputKeyboard",
    "MailingConfirmKeyboard",
    "AdminKeysListKeyboard",
    "AdminKeyDetailsKeyboard",
    "GenKeyInputTgIdKeyboard",
    "GenKeyChooseTariffKeyboard",
    "GenKeyConfirmKeyboard",
    "GenKeyResultKeyboard",
    "AdminDashboardKeyboard",
    "KeyStatsKeyboard",
    "PaymentStatsKeyboard",
    "InactiveUsersReviewKeyboard",
    "InactiveUsersConfirmKeyboard",
    "AdminMassRenewalSegmentKeyboard",
    "AdminMassRenewalInputDaysKeyboard",
    "AdminMassRenewalConfirmKeyboard",
]
