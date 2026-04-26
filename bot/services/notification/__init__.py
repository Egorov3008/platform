from .core import FunnelType, UserSegment, NotificationCondition
from .manager import FunnelManager
from .models import NotificationContext, NotificationResult, FunnelRunReport
from .protocols import NotificationFunnelProtocol
from .rate_limiter import RateLimiter
from .routing import KEY_SEGMENT_TO_FUNNEL, SENDING_HOUR_WINDOW, UserFunnelType

__all__ = [
    # Типы (обратная совместимость)
    "FunnelType",
    "UserSegment",
    "NotificationCondition",
    # Оркестратор
    "FunnelManager",
    # Модели
    "NotificationContext",
    "NotificationResult",
    "FunnelRunReport",
    # Протокол
    "NotificationFunnelProtocol",
    # Утилиты
    "RateLimiter",
    # Роутинг
    "KEY_SEGMENT_TO_FUNNEL",
    "SENDING_HOUR_WINDOW",
    "UserFunnelType",
]
