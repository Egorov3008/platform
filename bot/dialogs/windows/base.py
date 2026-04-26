from abc import ABC, abstractmethod
from typing import TypeVar, Callable, Any

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.widget_event import WidgetEventProcessor

T = TypeVar("T")


class DataGetter(ABC):
    """Абстрактный класс для получения данных."""

    @abstractmethod
    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        pass


class MessageBuilder(ABC):
    """Абстрактный класс для построения сообщений."""

    @abstractmethod
    def build(self) -> Text:
        pass


class KeyboardBuilder(ABC):
    """Абстрактный класс для построения клавиатур."""

    @abstractmethod
    def build(self) -> Keyboard:
        pass


class GenericSelectBuilder:
    """
    Универсальный билдер для создания Select-клавиатур в aiogram-dialog.
    Поддерживает кастомизацию: формат текста, ID, обработчик выбора.
    """

    def __init__(
        self,
        id: str,
        items_key: str,
        text_format: str = "{item[0]}",
        on_click: OnItemClick[Select[T], T] | WidgetEventProcessor | None = None,
        item_id_getter: Callable[[Any], str] = lambda x: str(x[1]),
        when: WhenCondition = None,
    ):
        self.widget = Select(
            Format(text_format),
            id=id,
            item_id_getter=item_id_getter,
            items=items_key,
            on_click=on_click,
            when=when,
        )

    def build(self) -> Select:
        return self.widget
