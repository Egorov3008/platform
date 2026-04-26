from typing import List, Dict, Any
from .base_registration import BaseRegistration


class RegistrationFactory:
    """Фабрика для регистрации по специальным ссылкам"""

    def __init__(self):
        self._handlers: List[BaseRegistration] = []

    def register_handler(self, handler: BaseRegistration):
        """Регистрирует обработчик"""
        handler_type = type(handler)
        if any(type(h) is handler_type for h in self._handlers):
            return
        self._handlers.append(handler)

    async def handle_registration(self, token: str) -> Dict[str, Any]:
        """Находит подходящий обработчик и выполняет регистрацию"""
        for handler in self._handlers:
            if await handler.can_handle(token):
                return await handler.register(token)
        return {"success": True, "type": "unknown_user"}
