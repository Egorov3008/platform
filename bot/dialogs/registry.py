from typing import Dict, List
from logger import logger
from aiogram import Router
from aiogram.fsm.state import StatesGroup
from aiogram_dialog import Window, Dialog
from punq import Container

from dialogs.windows import WindowFactory


class DialogRegistry:
    """Регистрирует окна и создает объекты Dialog, сгруппированные по StatesGroup."""

    def __init__(self, container: Container):
        self._factory = WindowFactory(container)
        self._windows: Dict[StatesGroup, List[Window]] = {}

    def add_from_configs(self, configs: List[dict]) -> None:
        """Добавить окна из конфигураций фабрики (с разрешением зависимостей через DI)."""
        for config in configs:
            state = config.get("state")
            state_group = state.group
            try:
                window = self._factory.create_window(**config)
            except Exception as e:
                logger.warning("Окно не создано, пропускаем", state=state, error=str(e))
                continue
            if state_group not in self._windows:
                self._windows[state_group] = []
            self._windows[state_group].append(window)

    def add_raw_windows(self, *windows: Window) -> None:
        """Добавить готовые объекты Window (для административных/устаревших диалогов)."""
        for window in windows:
            state_group = window.get_state().group
            if state_group not in self._windows:
                self._windows[state_group] = []
            self._windows[state_group].append(window)

    def build_router(self, name: str = "dialog") -> Router:
        """Создает Router с Dialog для каждого StatesGroup."""
        router = Router(name=name)
        for state_group, windows in self._windows.items():
            dialog = Dialog(*windows)
            router.include_router(dialog)
            logger.info(
                "Создан Dialog",
                state_group=state_group,
                windows=[w.get_state().state for w in windows],
            )
        return router
