import asyncio
from typing import Optional

from aiogram import Bot

from logger import logger


class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        self.running = False

    def get_status(self) -> dict:
        """Возвращает текущий статус фоновых задач."""
        return {
            "tasks_alive": {
                name: not task.done()
                for name, task in self.tasks.items()
            },
            "sync": {"last_run": None},
        }

    def is_notifications_enabled(self) -> bool:
        """Возвращает включены ли уведомления."""
        return False

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
