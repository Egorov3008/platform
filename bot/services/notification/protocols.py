"""
Протоколы (интерфейсы) для системы уведомлений.
"""

from typing import Protocol, runtime_checkable

from aiogram import Bot

from .models import NotificationContext, NotificationResult, FunnelRunReport


@runtime_checkable
class NotificationFunnelProtocol(Protocol):
    """Протокол воронки уведомлений."""

    funnel_id: str

    async def should_send(self, ctx: NotificationContext) -> bool:
        """Проверить, нужно ли отправлять уведомление в данном контексте."""
        ...

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        """Обработать контекст и отправить уведомление."""
        ...


@runtime_checkable
class NotificationStatsProtocol(Protocol):
    """Протокол сбора статистики уведомлений."""

    async def record(self, report: FunnelRunReport) -> None:
        """Записать отчёт о цикле уведомлений."""
        ...

    async def record_blocked(self, tg_id: int) -> None:
        """Зафиксировать, что пользователь заблокировал бота."""
        ...
