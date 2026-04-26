from typing import Type, Union, Any, Dict, List

from aiogram.fsm.state import State
from aiogram_dialog import Window
from punq import Container

from dialogs.windows.base import DataGetter, MessageBuilder, KeyboardBuilder
from logger import logger

TService = Union[Type[DataGetter], Type[KeyboardBuilder], Type[MessageBuilder]]


class WindowFactory:
    """
    Фабрика окон: создаёт Window для указанного состояния.
    Автоматически резолвит сервис через DI-контейнер и инжектит зависимости.
    """

    def __init__(self, container: Container):
        self.container = container
        self.registration_windows: Dict[Any, List[Window]] = {}

    def create_window(
        self,
        getter_cls: Type[DataGetter],
        keyboard_cls: Type[KeyboardBuilder],
        message_cls: Type[MessageBuilder],
        state: State,
        **kwargs,
    ) -> Window:
        """
        Создаёт Window для заданного сервиса и состояния.

        :param getter_cls: Подкласс DataGetter для getter'а (будет создан через DI)
        :param keyboard_cls: Подкласс KeyboardBuilder для клавиатуры (будет создан через DI)
        :param message_cls: Подкласс MessageBuilder для сообщения (будет создан через DI)
        :param state: Состояние окна
        :param kwargs: Доп. параметры для конструктора сервиса (если нужны)
        """
        # Резолвим сервис через DI + передаём доп. аргументы
        getter_service: DataGetter = self._create_dependence(getter_cls, **kwargs)
        keyboard_service: KeyboardBuilder = self._create_dependence(
            keyboard_cls, **kwargs
        )
        message_service: MessageBuilder = self._create_dependence(message_cls, **kwargs)

        keyboard_result = keyboard_service.build() if keyboard_service else None
        message_result = message_service.build()

        if isinstance(keyboard_result, (list, tuple)):
            return Window(
                message_result,
                *keyboard_result,
                state=state,
                getter=getter_service.get_data if getter_service else {},
            )
        return Window(
            message_result,
            *([keyboard_result] if keyboard_result is not None else []),
            state=state,
            getter=getter_service.get_data if getter_service else {},
        )

    def _create_dependence(self, service_cls: TService, **kwargs):
        try:
            if not service_cls:
                return None

            return self.container.resolve(service_cls, **kwargs)
        except Exception as e:
            import traceback
            logger.error(
                "Ошибка при создании сервиса",
                exc_info=True,
                name_service=service_cls.__name__,
                full_traceback=traceback.format_exc(),
            )
            raise

    def form_state_group(self, windows_state: List[Dict[Any, Any]]):
        """Формирует окна."""
        for data in windows_state:
            state = data.get("state")
            logger.debug("Регистрация окна", window=state)
            state_group = state.group
            window = self.create_window(**data)
            if state_group not in self.registration_windows:
                self.registration_windows[state_group] = []
            self.registration_windows[state_group].append(window)
        return self.registration_windows
