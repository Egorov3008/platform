from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseRegistration(ABC):
    """Абстрактный класс для регистрации по специальным ссылкам"""

    @abstractmethod
    async def can_handle(self, token: str) -> bool:
        """Проверяет, может ли обработчик работать с токеном"""
        pass

    @abstractmethod
    async def register(self, token: str) -> Dict[str, Any]:
        """Выполняет регистрацию и возвращает результат"""
        pass
