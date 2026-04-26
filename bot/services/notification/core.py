"""
Базовые типы и условия системы уведомлений.

FunnelStrategy удалён: воронки реализуют NotificationFunnelProtocol напрямую.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, List, Callable, Optional

from models import Key, User
from services.core.time_helper import TimeHelper


class FunnelType(Enum):
    """Идентификаторы воронок (для обратной совместимости)."""

    KEY_EXPIRY_24H = "key_expiry_24h"
    KEY_EXPIRY_10H = "key_expiry_10h"
    TRIAL_REMINDER = "trial_unused"


class UserSegment(Enum):
    """Сегменты пользователей."""

    NEW_USER = "new_user"
    ACTIVE_TRIAL = "active_trial"
    ACTIVE_PAID = "active_paid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED_PAID = "expired_paid"
    INACTIVE = "inactive"
    INACTIVE_TRIAL = "inactive_trial"
    CHURN_RISK = "churn_risk"
    COLD_LEAD = "cold_lead"


class NotificationCondition(ABC):
    """Абстрактный класс условий для уведомлений."""

    @abstractmethod
    async def check(self, user_data: Dict[str, Any]) -> bool:
        pass


class BaseCondition(NotificationCondition):
    """Базовый класс с общими методами."""

    def __init__(self):
        self.time = TimeHelper()

    def _extract_user_data(self, user_data: Dict[str, Any]) -> tuple:
        user = user_data.get("user")
        keys = user_data.get("keys", [])
        if not user:
            raise ValueError("User data is missing 'user' field")
        return user, keys

    def _is_paid_tariff(self, tariff_id: Optional[int]) -> bool:
        return tariff_id not in (10, None)

    def _filter_keys(
        self,
        keys: List[Key],
        tariff_filter: Optional[Callable[[Optional[int]], bool]] = None,
        expiry_filter: Optional[Callable[[int], bool]] = None,
        usage_filter: Optional[Callable[[float], bool]] = None,
    ) -> List[Key]:
        filtered = []
        for key in keys:
            if (
                tariff_filter
                and key.tariff_id is not None
                and not tariff_filter(key.tariff_id)
            ):
                continue
            if expiry_filter and not expiry_filter(key.expiry_time):
                continue
            if (
                usage_filter
                and key.total_gb is not None
                and not usage_filter(float(key.total_gb))
            ):
                continue
            filtered.append(key)
        return filtered

    def get_active_paid_keys(self, keys: List[Key]) -> List[Key]:
        return self._filter_keys(
            keys,
            tariff_filter=lambda tid: self._is_paid_tariff(tid),
            expiry_filter=lambda exp: exp >= self.time.now_ms,
        )

    def get_expired_paid_keys(self, keys: List[Key]) -> List[Key]:
        return self._filter_keys(
            keys,
            tariff_filter=lambda tid: self._is_paid_tariff(tid),
            expiry_filter=lambda exp: exp < self.time.now_ms,
        )

    def get_keys_expiring_in_24h(self, keys: List[Key]) -> List[Key]:
        return self._filter_keys(
            keys,
            expiry_filter=lambda exp: (
                self.time.now_ms < exp <= self.time.twenty_four_hours_ms
            ),
        )


class SimpleCondition(BaseCondition):
    """Декларативные условия через список правил."""

    def __init__(self, rules: List[Callable]):
        super().__init__()
        self.rules = rules

    async def check(self, user_data: Dict[str, Any]) -> bool:
        user, keys = self._extract_user_data(user_data)
        try:
            return all(rule(user, keys) for rule in self.rules)
        except Exception as e:
            from logger import logger

            logger.error("Ошибка при определении сегмента пользователя", error=str(e))
            return False


def new_user_condition() -> "SimpleCondition":
    """trial=0, нет ключей, регистрация 1-15 дней назад."""

    def check(user: User, keys: List[Key]) -> bool:
        if user.trial != 0 or keys:
            return False
        if not user.created_at:
            return True
        now = datetime.now(timezone.utc)
        created = (
            user.created_at
            if user.created_at.tzinfo
            else user.created_at.replace(tzinfo=timezone.utc)
        )
        days_ago = (now - created).days
        return 1 <= days_ago <= 15

    return SimpleCondition([check])


def cold_lead_condition() -> "SimpleCondition":
    """trial=0, нет ключей, регистрация >15 дней назад."""

    def check(user: User, keys: List[Key]) -> bool:
        if user.trial != 0 or keys:
            return False
        if not user.created_at:
            return False
        now = datetime.now(timezone.utc)
        created = (
            user.created_at
            if user.created_at.tzinfo
            else user.created_at.replace(tzinfo=timezone.utc)
        )
        return (now - created).days > 15

    return SimpleCondition([check])


def inactive_trial_condition() -> "SimpleCondition":
    """trial=1, есть неиспользуемые trial-ключи старше 2 дней."""

    def check(user: User, keys: List[Key]) -> bool:
        if user.trial != 1:
            return False
        now = datetime.now(timezone.utc)
        return any(
            key.tariff_id == 10
            and datetime.fromtimestamp(key.created_at / 1000, tz=timezone.utc)
            < now - timedelta(days=2)
            and (key.total_gb or 0.0) == 0.0
            for key in keys
        )

    return SimpleCondition([check])


def expiring_keys_condition(hours: int = 24) -> "SimpleCondition":
    """Ключи истекают в ближайшие N часов."""

    def check(_: User, keys: List[Key]) -> bool:
        now_ms = datetime.now().timestamp() * 1000
        threshold_ms = now_ms + hours * 3600 * 1000
        return any(now_ms < key.expiry_time <= threshold_ms for key in keys)

    return SimpleCondition([check])


class UserSegmenter:
    """Определитель сегмента пользователя."""

    def __init__(self) -> None:
        self.segment_rules: List[tuple] = [
            (UserSegment.EXPIRING_SOON, expiring_keys_condition(24)),
            (UserSegment.NEW_USER, new_user_condition()),
            (UserSegment.COLD_LEAD, cold_lead_condition()),
            (UserSegment.INACTIVE_TRIAL, inactive_trial_condition()),
        ]
        self._cache: dict = {}

    async def determine_segment(self, user_data: Dict[str, Any]) -> UserSegment:
        user: Optional[User] = user_data.get("user")
        if not user:
            return UserSegment.INACTIVE

        cache_key = f"{user.tg_id}_{int(datetime.now().timestamp() // 300)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        for segment, condition in self.segment_rules:
            if await condition.check(user_data):
                self._cache[cache_key] = segment
                return segment

        self._cache[cache_key] = UserSegment.INACTIVE
        return UserSegment.INACTIVE
