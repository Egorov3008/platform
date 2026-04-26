"""
Клавиатура для проверки подписки на канал.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_URL


def create_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт inline-клавиатуру с кнопками:
    - "Подписаться на канал" (ссылка на канал)
    - "✅ Я подписался" (callback для проверки)
    
    Если CHANNEL_URL не задан — возвращает клавиатуру без кнопки подписки.
    """
    buttons = []
    
    # Кнопка подписки только если CHANNEL_URL задан
    if CHANNEL_URL:
        buttons.append([
            InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=CHANNEL_URL,
            ),
        ])
    
    # Кнопка проверки
    buttons.append([
        InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="subscription_check",
        ),
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def create_check_subscription_only_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт inline-клавиатуру только с кнопкой проверки.
    Используется когда пользователь уже подписался и нужно только проверить.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Проверить подписку",
                    callback_data="subscription_check",
                ),
            ],
        ],
    )
    return keyboard
