"""Геттер окна мониторинга (Dashboard) для admin-панели."""

from typing import Any, Dict

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger
from tasks import task_manager


class AdminDashboardGetter(DataGetter):
    """Геттер для окна мониторинга состояния бота.

    Показывает статус задач, базовую статистику с backend
    и состояние уведомлений.
    """

    def __init__(self, backend: BackendAPIClient) -> None:
        self._backend = backend

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            status = task_manager.get_status()
            # Fetch basic counts from backend
            try:
                users = await self._backend.admin_list_users()
                keys = await self._backend.admin_list_keys()
                payments = await self._backend.admin_list_payments()
                total_revenue = sum(
                    float(p.get("amount", 0)) for p in payments if p.get("status") == "succeeded"
                )
                backend_info = (
                    f"👤 Пользователей: {len(users)}\n"
                    f"🔑 Ключей: {len(keys)}\n"
                    f"💳 Платежей: {len(payments)}  |  Выручка: {total_revenue:,.0f} руб"
                )
            except Exception as e:
                logger.warning("Dashboard backend fetch failed", error=str(e))
                backend_info = "❌ Не удалось загрузить статистику с backend"

            sync = status.get("sync", {"last_run": None})
            sync_age = "н/д"
            if sync["last_run"]:
                import time
                delta = time.time() - sync["last_run"]
                if delta < 60:
                    sync_age = "только что"
                elif delta < 3600:
                    sync_age = f"{int(delta // 60)} мин назад"
                else:
                    sync_age = f"{int(delta // 3600)} ч назад"

            tasks_alive = status.get("tasks_alive", {})
            task_lines = "  |  ".join(
                f"{name}: {'✅' if alive else '❌'}"
                for name, alive in tasks_alive.items()
            )

            text = (
                "<b>📊 Статус бота</b>\n\n"
                f"🔄 <b>Синхронизация</b>\n"
                f"  Последний запуск: {sync_age}\n\n"
                f"{backend_info}\n\n"
                f"⚙️ <b>Задачи</b>\n  {task_lines}"
            )

            notifications_status = (
                "🔔 Уведомления: ВКЛ"
                if getattr(task_manager, "is_notifications_enabled", lambda: False)()
                else "🔕 Уведомления: ВЫКЛ"
            )
            return {
                "DASHBOARD_MSG": text,
                "notifications_status": notifications_status,
            }
        except Exception as e:
            logger.error("Ошибка при сборке статуса бота", error=str(e), exc_info=True)
            return {
                "DASHBOARD_MSG": f"❌ Ошибка при загрузке статуса: {e}",
                "notifications_status": "🔕 Уведомления: н/д",
            }
