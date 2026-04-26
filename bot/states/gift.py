# states/main.py
from aiogram.filters.state import StatesGroup, State


class GiftStates(StatesGroup):
    main = State()  # Окно с ссылкой
    activate_gift = State()  # Подтверждение активации
    success = State()  # Успешная активация
    error = State()  # Ошибка
    not_found = State()  # Подарок не найден
    already_used = State()  # Уже использован
