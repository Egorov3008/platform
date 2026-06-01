import asyncio
from typing import Optional

from aiogram import Bot

from logger import logger


class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        self.running = False
        self._notifications_enabled = True

    def get_status(self) -> dict:
        """Возвращает текущий статус фоновых задач."""
        return {
            "tasks_alive": {
                name: not task.done()
                for name, task in self.tasks.items()
            },
            "sync": {"last_run": None, "duration": None, "error_count": 0},
            "notifications": {
                "enabled": self._notifications_enabled,
                "last_run": None,
                "report": None,
            },
        }

    def is_notifications_enabled(self) -> bool:
        """Возвращает включены ли уведомления."""
        return self._notifications_enabled

    def enable_notifications(self) -> None:
        """Включить уведомления (stub — backend управляет фактическими задачами)."""
        self._notifications_enabled = True
        logger.info("Уведомления включены (stub)")

    def disable_notifications(self) -> None:
        """Выключить уведомления (stub — backend управляет фактическими задачами)."""
        self._notifications_enabled = False
        logger.info("Уведомления выключены (stub)")

    async def start_all_tasks(self, container, bot: Bot) -> None:
        """Запуск всех фоновых задач."""
        self.running = True
        logger.info("Фоновые задачи запущены (none active)")

    async def stop_all_tasks(self) -> None:
        """Остановка всех фоновых задач."""
        self.running = False
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                logger.info("Остановка задачи", task_name=name)

        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        logger.info("Все фоновые задачи остановлены")


# Глобальный менеджер
task_manager = BackgroundTaskManager()
