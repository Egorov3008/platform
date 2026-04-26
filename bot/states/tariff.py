from aiogram.fsm.state import StatesGroup, State


class Tariff(StatesGroup):
    preview = State()
