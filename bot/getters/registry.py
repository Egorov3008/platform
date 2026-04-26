from typing import Dict, Callable, Any, Optional
from aiogram_dialog import DialogManager

# Тип: getter — это асинхронная функция, возвращающая dict
Getter = Callable[[DialogManager, Dict[Any, Any]], Dict[str, Any]]

# Глобальный реестр: state -> getter
GETTER_REGISTRY: Dict[str, Getter] = {}


def register_getter(state: str):
    """Декоратор для регистрации getter'а под определённый state."""

    def decorator(func: Getter) -> Getter:
        GETTER_REGISTRY[state] = func
        return func

    return decorator


def get_getter(state: str) -> Optional[Getter]:
    """
    Получить getter по state.
    """
    return GETTER_REGISTRY.get(state)


# Удобная функция для массовой регистрации
def register_getters_from_module(module):
    """
    Регистрирует все функции, отмеченные @register_getter, из модуля.
    """
    # Просто импортируем модуль — декораторы выполнятся при import
    pass
