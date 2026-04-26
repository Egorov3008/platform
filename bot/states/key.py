from aiogram.filters.state import StatesGroup, State


class KeysInit(StatesGroup):
    confirmation_delete_key = State()
    create_key = State()
    create_trial = State()
    create_gift_key = State()
    edition = State()
    renewal = State()
    list = State()
    key = State()
    error = State()
