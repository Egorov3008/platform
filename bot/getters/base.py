from abc import ABC, abstractmethod
from typing import Callable, Dict, Any

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram_dialog.widgets.text import Text

Getter = Callable[[DialogManager, Dict[Any, Any]], Dict[str, Any]]


class BaseService(ABC):
    """Базовый класс для формирования getter для window по target_state: StateGroup:State"""

    def __init__(self, target_state: str):
        self.target_state = target_state

    @abstractmethod
    async def designer_getters(self, *args, **kwargs) -> Dict[str, Any]:
        """Формирует данные для определенного state"""
        pass

    @abstractmethod
    def designer_msg(self) -> Text:
        """Формирует сообщение для определенного state"""
        pass

    @abstractmethod
    def designer_keyboard(self) -> Keyboard:
        """Формирует клавиатуру для определенного state"""
        pass
