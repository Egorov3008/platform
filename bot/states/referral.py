from aiogram.filters.state import State, StatesGroup


class ReferralSistem(StatesGroup):
    main = State()
    generate_form = State()
