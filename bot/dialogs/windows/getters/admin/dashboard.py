"""Геттер окна мониторинга (Dashboard) для admin-панели."""

from typing import Any, Dict

import asyncpg
from aiogram_dialog import DialogManager

from client import XUISession
from dialogs.windows.base import DataGetter
from logger import logger
from services.bot_status import BotStatusService
from services.cache.service import CacheService
from tasks import task_manager


class AdminDashboardGetter(DataGetter):
    """Геттер для окна мониторинга состояния бота.

    Показывает статус синхронизации, уведомлений, кэша,
    3x-ui панели, платежей, рефералов и подарков.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        cache_service: CacheService,
        xui_session: XUISession,
    ) -> None:
        self._db_pool = db_pool
        self._cache_service = cache_service
        self._xui_session = xui_session

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            async with self._db_pool.acquire() as conn:
                text = await BotStatusService.build_status(
                    task_manager=task_manager,
                    # Прямой доступ к _storage допустим: только чтение размеров namespace,
                    # CacheService API не предоставляет метод подсчёта элементов.
                    cache_storage=self._cache_service.storage,
                    cache_service=self._cache_service,
                    xui_session=self._xui_session,
                    db_conn=conn,
                )
            notifications_status = "🔔 Уведомления: ВКЛ" if task_manager.is_notifications_enabled() else "🔕 Уведомления: ВЫКЛ"
            return {
                "DASHBOARD_MSG": text,
                "notifications_status": notifications_status,
            }
        except Exception as e:
            logger.error("Ошибка при сборке статуса бота", error=str(e), exc_info=True)
            return {"DASHBOARD_MSG": f"❌ Ошибка при загрузке статуса: {e}"}
