"""
Маппинг сегментов ключей → воронки уведомлений.
"""

from enum import Enum

from services.core.segmentation.key_model import KeySegment

# Разрешённое временное окно отправки (часы, включительно-исключительно)
SENDING_HOUR_WINDOW: tuple[int, int] = (8, 23)

# Маппинг: сегмент ключа → funnel_id (key-based воронки)
KEY_SEGMENT_TO_FUNNEL: dict[KeySegment, str] = {
    KeySegment.EXPIRING_10H: "key_expiry_10h",
    KeySegment.EXPIRING_24H: "key_expiry_24h",
    KeySegment.TRIAL: "trial_unused",
}


class UserFunnelType(Enum):
    """Идентификаторы воронок по пользователю (не по ключу)."""

    COLD_LEAD = "cold_lead"
