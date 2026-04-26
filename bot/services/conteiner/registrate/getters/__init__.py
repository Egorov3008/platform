from .profile import ProfileRegistrar
from .gift import GiftRegistrar
from .payment import PaymentRegistrar
from .tariff import TariffGetterRegistration
from .keys import KeysRegistrar
from .register import RegisterRegistrar
from .instruction import InstructionRegistrar
from .usage_rules import UsageRulesRegistrar
from .admin import AdminRegistrar
from .referral import ReferralRegistrar

__all__ = [
    ProfileRegistrar,
    GiftRegistrar,
    PaymentRegistrar,
    TariffGetterRegistration,
    KeysRegistrar,
    RegisterRegistrar,
    InstructionRegistrar,
    UsageRulesRegistrar,
    AdminRegistrar,
    ReferralRegistrar,
]
