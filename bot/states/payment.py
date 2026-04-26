from aiogram.fsm.state import StatesGroup, State


class PaymentState(StatesGroup):
    view_tariff = State()
    form_pay = State()
    result_pay = State()
    setting_pay = State()
