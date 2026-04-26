from unittest.mock import Mock

from aiogram.fsm.state import StatesGroup, State
from getters.base import BaseService
from getters.registor.registrate import RegistrateService, StateKey


def test_state_key_full_property():
    """Тестирует, что full возвращает правильное значение"""
    key = StateKey(states_group="TestGroup", state="test_state")
    assert key.full == "TestGroup:test_state"


def test_state_key_hash_and_equality():
    """Тестирует, что StateKey корректно работает с хэшем и равенством"""
    key1 = StateKey(states_group="Group", state="state")
    key2 = StateKey(states_group="Group", state="state")
    key3 = StateKey(states_group="Group", state="other")

    assert hash(key1) == hash(key2)
    assert key1 == key2
    assert key1 != key3
    assert key1 != "some_string"


class TestStatesGroup(StatesGroup):
    """Тестовая группа состояний"""

    state1 = State()
    state2 = State()


def test_registrate_service_collect_state_keys():
    """Тестирует, что сервис правильно собирает ключи состояний"""
    service = RegistrateService(states=[TestStatesGroup], services=[])
    service._collect_state_keys()

    expected_keys = [
        StateKey(states_group="TestStatesGroup", state="state1"),
        StateKey(states_group="TestStatesGroup", state="state2"),
    ]

    assert len(service.states_keys) == 2
    assert all(key in service.states_keys for key in expected_keys)


def test_registrate_service_map_services_to_states():
    """Тестирует, что сервис правильно сопоставляет сервисы и состояния"""
    # Создаем mock сервисы с target_state
    service1 = Mock(spec=BaseService)
    service1.target_state = "TestStatesGroup:state1"

    service2 = Mock(spec=BaseService)
    service2.target_state = "TestStatesGroup:state2"

    service3 = Mock(spec=BaseService)  # Без target_state

    service = RegistrateService(
        states=[TestStatesGroup], services=[service1, service2, service3]
    )
    service._collect_state_keys()
    service._map_services_to_states()

    # Проверяем, что сервисы правильно сопоставились
    expected_key1 = StateKey(states_group="TestStatesGroup", state="state1")
    expected_key2 = StateKey(states_group="TestStatesGroup", state="state2")

    assert expected_key1 in service.service_registry
    assert service.service_registry[expected_key1] == service1
    assert expected_key2 in service.service_registry
    assert service.service_registry[expected_key2] == service2
    assert (
        len(service.service_registry) == 2
    )  # Только два сервиса должны быть зарегистрированы


def test_registrate_service_register():
    """Тестирует, что сервис правильно регистрирует сервисы"""
    service1 = Mock(spec=BaseService)
    service1.target_state = "TestStatesGroup:state1"

    service = RegistrateService(states=[TestStatesGroup], services=[service1])
    registry = service.register()

    expected_key = StateKey(states_group="TestStatesGroup", state="state1")
    assert expected_key in registry
    assert registry[expected_key] == service1

    # Проверяем, что возвращается копия, а не оригинальный словарь
    assert registry is not service.service_registry
