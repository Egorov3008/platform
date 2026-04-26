import asyncio
from unittest.mock import Mock

import pytest
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Window, DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const
from punq import Container

from dialogs.windows.base import DataGetter, MessageBuilder, KeyboardBuilder
from dialogs.windows.window_factory import WindowFactory


class MockDataGetter(DataGetter):
    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        return {"test": "data"}


class MockMessageBuilder(MessageBuilder):
    def build(self):
        return Const("Test message")


class MockKeyboardBuilder(KeyboardBuilder):
    def build(self):
        return Button(Const("Test keyboard"), id="test")


def test_window_factory_init():
    # Arrange
    container = Mock(spec=Container)

    # Act
    factory = WindowFactory(container)

    # Assert
    assert factory.container == container


def test_window_factory_create_all_dependencies_success():
    """Тест для проверки успешного создания окна со всеми зависимостями."""
    # Arrange
    container = Mock(spec=Container)
    state = State()

    mock_getter = MockDataGetter()
    mock_keyboard = MockKeyboardBuilder()
    mock_message = MockMessageBuilder()

    container.resolve.side_effect = lambda cls, **kwargs: {
        MockDataGetter: mock_getter,
        MockKeyboardBuilder: mock_keyboard,
        MockMessageBuilder: mock_message,
    }[cls]

    factory = WindowFactory(container)

    # Act
    window = factory.create_window(
        getter_cls=MockDataGetter,
        keyboard_cls=MockKeyboardBuilder,
        message_cls=MockMessageBuilder,
        state=state,
    )

    # Mock для вызова getter и render_text
    dialog_manager = Mock(spec=DialogManager)
    dialog_manager.middleware_data = {}
    dialog_manager.event = Mock(from_user=Mock(id=1, first_name="Test"))

    # Assert
    assert isinstance(window, Window)
    assert window.state == state

    # Проверка текста
    text = asyncio.run(window.render_text({}, dialog_manager))
    assert text == "Test message"

    # Проверка клавиатуры

    assert window.keyboard.widget_id == "test"

    # Проверка getter
    assert window.getter is not None
    data = asyncio.run(window.getter(dialog_manager))
    assert isinstance(data, dict)

    # Проверка вызовов resolve
    assert container.resolve.call_count == 3
    container.resolve.assert_any_call(MockDataGetter)
    container.resolve.assert_any_call(MockKeyboardBuilder)
    container.resolve.assert_any_call(MockMessageBuilder)


def test_window_factory_create_with_kwargs():
    """Тест для проверки создания окна с дополнительными параметрами."""
    # Arrange
    container = Mock(spec=Container)
    state = State()

    container.resolve.side_effect = lambda cls, **kwargs: {
        MockDataGetter: MockDataGetter(),
        MockKeyboardBuilder: MockKeyboardBuilder(),
        MockMessageBuilder: MockMessageBuilder(),
    }[cls]

    factory = WindowFactory(container)

    # Act
    window = factory.create_window(
        getter_cls=MockDataGetter,
        keyboard_cls=MockKeyboardBuilder,
        message_cls=MockMessageBuilder,
        state=state,
        extra_param="test",
    )

    # Assert
    assert isinstance(window, Window)
    assert window.state == state


def test_window_factory_create_dependency_error():
    """Тест для проверки обработки ошибок при создании окна."""
    # Arrange
    container = Mock(spec=Container)
    container.resolve.side_effect = Exception("DI error")
    state = State()
    factory = WindowFactory(container)

    # Act & Assert
    with pytest.raises(Exception, match="DI error"):
        factory.create_window(
            getter_cls=MockDataGetter,
            keyboard_cls=MockKeyboardBuilder,
            message_cls=MockMessageBuilder,
            state=state,
        )


def test_window_factory_create_partial_dependency_error():
    """Тест для проверки обработки ошибок при создании окна с частичной зависимостью."""
    # Arrange
    container = Mock(spec=Container)
    state = State()

    calls = 0

    def resolve_side_effect(cls, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return MockDataGetter()
        raise Exception("Keyboard DI error")

    container.resolve.side_effect = resolve_side_effect

    factory = WindowFactory(container)

    # Act & Assert
    with pytest.raises(Exception, match="Keyboard DI error"):
        factory.create_window(
            getter_cls=MockDataGetter,
            keyboard_cls=MockKeyboardBuilder,
            message_cls=MockMessageBuilder,
            state=state,
        )


def test_form_state_group():
    """Тест для проверки формирования группы окон."""
    # Arrange
    container = Mock(spec=Container)

    class TestState(StatesGroup):
        state1 = State()
        state2 = State()
        state3 = State()

    mock_getter = MockDataGetter()
    mock_keyboard = MockKeyboardBuilder()
    mock_message = MockMessageBuilder()

    container.resolve.side_effect = lambda cls, **kwargs: {
        MockDataGetter: mock_getter,
        MockKeyboardBuilder: mock_keyboard,
        MockMessageBuilder: mock_message,
    }[cls]

    factory = WindowFactory(container)

    windows_data = [
        {
            "getter_cls": MockDataGetter,
            "keyboard_cls": MockKeyboardBuilder,
            "message_cls": MockMessageBuilder,
            "state": TestState.state1,
        },
        {
            "getter_cls": MockDataGetter,
            "keyboard_cls": MockKeyboardBuilder,
            "message_cls": MockMessageBuilder,
            "state": TestState.state2,
        },
        {
            "getter_cls": MockDataGetter,
            "keyboard_cls": MockKeyboardBuilder,
            "message_cls": MockMessageBuilder,
            "state": TestState.state3,
        },
    ]

    # Act
    factory.form_state_group(windows_data)

    # Assert
    assert TestState in factory.registration_windows

    assert len(factory.registration_windows[TestState]) == 3
    assert all(isinstance(w, Window) for w in factory.registration_windows[TestState])
