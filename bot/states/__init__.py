from dataclasses import dataclass
from .admin import (
    AdminManager,
    AdminUserManagement,
    AdminSearchManagementSG,
    AdminMassMailing,
    AdminKeyDeleteSG,
    AdminKeyChangeDateSG,
    AdminKeyChangeTariffSG,
    AdminGenerateKeySG,
    AdminUserDeleteSG,
    AdminUserCleanupSG,
    AdminMassRenewal,
)
from .gift import GiftStates
from .instruction import Instruction
from .key import KeysInit
from .main import MainMenu
from .referral import ReferralSistem
from .registrate import Register
from .rulse import UsageRules
from .tariff import Tariff
from .payment import PaymentState

__all__ = [
    MainMenu,
    GiftStates,
    KeysInit,
    ReferralSistem,
    AdminManager,
    AdminUserManagement,
    AdminSearchManagementSG,
    AdminMassMailing,
    AdminKeyDeleteSG,
    AdminKeyChangeDateSG,
    AdminKeyChangeTariffSG,
    AdminGenerateKeySG,
    AdminUserDeleteSG,
    AdminUserCleanupSG,
    AdminMassRenewal,
    Instruction,
    Register,
    Tariff,
    PaymentState,
    UsageRules,
]


@dataclass
class StateKey:
    """Ключ для реестра: группа состояний + конкретное состояние"""

    states_group: str
    state: str

    @property
    def full(self) -> str:
        """Полное имя состояния: Group:state"""
        return f"{self.states_group}:{self.state}"

    def __hash__(self):
        return hash((self.states_group, self.state))

    def __eq__(self, other):
        if isinstance(other, StateKey):
            return self.full == other.full
        return False
