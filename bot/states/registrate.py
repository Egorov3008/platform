from aiogram.filters.state import State, StatesGroup


class Register(StatesGroup):
    captcha = State()
