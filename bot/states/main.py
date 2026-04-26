from aiogram.filters.state import StatesGroup, State


class MainMenu(StatesGroup):
    welcome = State()
    main = State()
    min_main = State()
