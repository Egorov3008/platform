"""
Обработчик callback_query для проверки подписки на канал.
"""

import json
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest

from logger import logger
from config import CHANNEL_URL
from utils_bot.subscription_checker import check_user_subscription
from utils_bot.subscription_keyboard import create_check_subscription_only_keyboard

router = Router()


async def _get_return_keyboard(context: Optional[dict]) -> Optional[InlineKeyboardMarkup]:
    """
    Создаёт клавиатуру для возврата к исходному действию.
    """
    if not context:
        return None

    callback_data = context.get("callback_data")
    message_text = context.get("message_text")

    buttons = []

    # Если было продление ключа
    if callback_data and "renew" in callback_data.lower():
        buttons.append([
            InlineKeyboardButton(
                text="↩️ Вернуться к продлению",
                callback_data=callback_data,
            ),
        ])

    # Если был запрос ключа
    elif callback_data and ("create" in callback_data.lower() or "key" in callback_data.lower()):
        buttons.append([
            InlineKeyboardButton(
                text="↩️ Вернуться к получению ключа",
                callback_data=callback_data,
            ),
        ])

    # Если была оплата
    elif callback_data and "payment" in callback_data.lower():
        buttons.append([
            InlineKeyboardButton(
                text="↩️ Вернуться к оплате",
                callback_data=callback_data,
            ),
        ])

    # Для остальных случаев — кнопка в профиль
    else:
        buttons.append([
            InlineKeyboardButton(
                text="👤 Перейти в профиль",
                callback_data="profile",
            ),
        ])

    # Всегда добавляем кнопку "Главное меню"
    buttons.append([
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu",
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "subscription_check")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot) -> None:
    """
    Обработчик нажатия на кнопку "✅ Я подписался" / "🔄 Проверить подписку".

    Проверяет подписку пользователя на канал и:
    - Если подписан — отправляет сообщение об успехе с кнопкой возврата
    - Если не подписан — напоминает о необходимости подписки
    """
    if not CHANNEL_URL:
        await callback.answer(
            "⚠️ CHANNEL_URL не настроен. Обратитесь к администратору.",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id

    # Получаем кэш из состояния (через bot.get_state().get_data())
    cache = None
    try:
        from services.conteiner.app import get_container
        from services.cache.service import CacheService

        container = await get_container()
        cache = container.resolve(CacheService)
    except Exception as e:
        logger.warning("Не удалось получить кэш для проверки подписки", error=str(e))

    # Проверяем подписку с кэшированием
    is_subscribed = await check_user_subscription(bot, user_id, cache)

    if is_subscribed:
        # Очищаем кэш подписки чтобы следующая проверка была актуальной
        if cache:
            try:
                await cache.storage.delete(namespace="subscription", key=str(user_id))
            except Exception:
                pass

        # Пытаемся восстановить контекст
        context = None
        if cache:
            try:
                context_json = await cache.storage.get(namespace="subscription", key=f"return_to:{user_id}")
                if context_json:
                    context = json.loads(context_json)
                    # Очищаем контекст
                    await cache.storage.delete(namespace="subscription", key=f"return_to:{user_id}")
            except Exception as e:
                logger.warning(
                    "Ошибка при чтении контекста подписки",
                    user_id=user_id,
                    error=str(e),
                )

        # Создаём клавиатуру для возврата
        keyboard = await _get_return_keyboard(context)

        await callback.message.edit_text(
            text=(
                "✅ <b>Подписка подтверждена!</b>\n\n"
                "Теперь у вас есть доступ ко всем функциям бота.\n\n"
                "Выберите действие:"
            ),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        logger.info(
            "Подписка подтверждена пользователем",
            user_id=user_id,
            had_context=context is not None,
        )
    else:
        # Пользователь всё ещё не подписан
        keyboard = create_check_subscription_only_keyboard()
        await callback.answer(
            "❌ Вы ещё не подписались на канал",
            show_alert=True,
        )
        try:
            await callback.message.edit_text(
                text=(
                    "❌ <b>Подписка не обнаружена</b>\n\n"
                    "Похоже, вы ещё не подписались на наш канал.\n\n"
                    "👇 Перейдите в канал, подпишитесь, а затем нажмите кнопку проверки"
                ),
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except TelegramBadRequest:
            # Сообщение уже содержит этот текст — ничего не делаем
            pass
        logger.debug(
            "Пользователь не подписался после нажатия кнопки проверки",
            user_id=user_id,
        )
