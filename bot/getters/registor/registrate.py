from typing import Dict, Any, List

from aiogram.fsm.state import StatesGroup

from getters.base import BaseService
from states import StateKey


class RegistrateService:
    """Реестр сервисов: сопоставляет состояния FSM с соответствующими сервисами"""

    def __init__(self, states: List[StatesGroup], services: List[BaseService]):
        self.states_groups = states
        self.services = services
        self.states_keys: List[StateKey] = []
        self.service_registry: Dict[StateKey, Any] = {}

    def _collect_state_keys(self) -> None:
        """Собирает все StateKey из всех групп состояний"""
        self.states_keys.clear()
        for state_group in self.states_groups:
            for full_state_name in state_group.__all_states_names__:
                try:
                    group_name, state_name = full_state_name.split(":", 1)
                    self.states_keys.append(
                        StateKey(states_group=group_name, state=state_name)
                    )
                except ValueError:
                    continue

    def _map_services_to_states(self) -> None:
        """Сопоставляет сервисы с состояниями по полному имени target_state"""
        self.service_registry.clear()

        for service in self.services:
            target_full: str = getattr(service, "target_state", None)

            if not target_full:
                continue

            for state_key in self.states_keys:
                if state_key.full == target_full:
                    self.service_registry[state_key] = service
                    break

    def register(self) -> Dict[StateKey, Any]:
        """
        Регистрирует сервисы.
        Возвращает: {StateKey(group, state): designer_getters}
        """
        self._collect_state_keys()
        self._map_services_to_states()
        return self.service_registry.copy()
