# dialogs/conditions.py
"""
Унифицированные условия для `when` в кнопках.
Пример: when: trial -> будет вызван соответствующий лямбда-предикат.
"""

from typing import Callable, Any


def compile_condition(name: str) -> Callable[[dict, Any, Any], bool]:
    """
    Возвращает callable-условие по строковому ключу.

    :param name: Название условия (из YAML)
    :return: Функция вида (data, widget, manager) -> bool
    """
    CONDITIONS = {
        "trial": lambda d, w, m: bool(d.get("trial")),
        "not_trial_tariff": lambda d, w, m: not d.get("is_trial", False),
        "check_key": lambda d, w, m: d.get("count_key", 0) > 0,
        "is_admin": lambda d, w, m: bool(d.get("is_admin")),
        "token": lambda d, w, m: bool(d.get("token")),
        "check_usage_link": lambda d, w, m: bool(d.get("referral_link")),
        "state_key_manager": lambda d, w, m: d.get("flow") == "key_manager",
        "state_search": lambda d, w, m: d.get("flow") == "search",
    }
    return CONDITIONS.get(name, lambda d, w, m: True)  # По умолчанию — показываем
