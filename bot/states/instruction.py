from aiogram.filters.state import StatesGroup, State


class Instruction(StatesGroup):
    choosing_device = State()
    android = State()
    iphone = State()
    windows = State()
    linux = State()
