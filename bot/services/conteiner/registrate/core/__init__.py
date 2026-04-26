from .cache import CacheRegistrar
from .coreservice import CoreServiceRegistrar
from .gift import GiftServiceRegistrar
from .keys import KeyServiceRegistrar
from .users import UserServiceRegistrar
from .tariff import TariffServiceRegistrar
from .registration import RegistrationRegistrar

__all__ = [
    CacheRegistrar,
    CoreServiceRegistrar,
    GiftServiceRegistrar,
    KeyServiceRegistrar,
    UserServiceRegistrar,
    TariffServiceRegistrar,
    RegistrationRegistrar,
]
