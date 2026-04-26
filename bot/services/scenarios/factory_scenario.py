from abc import ABC, abstractmethod

from aiogram_dialog import DialogManager


class ScenarioFactory(ABC):
    """Абстрактная фабрика сценариев — определяет общий интерфейс"""

    def __init__(self, dialog_manager: DialogManager):
        self.dialog_manager = dialog_manager

    @abstractmethod
    async def start(self, **kwargs) -> None:
        """Запускает сценарий: открывает нужное окно, создаёт ключ, отправляет сообщение"""
        pass

    @abstractmethod
    async def can_handle(self, **kwargs) -> bool:
        """Проверяет, может ли этот сценарий обработать текущего пользователя"""
        pass

    @abstractmethod
    async def get_data(self, **kwargs):
        pass
