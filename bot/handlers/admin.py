"""Handlers для администраторских функций."""

from aiogram import Router, F
from aiogram.filters import Filter, Command
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode

from config import ADMIN_ID
from logger import logger
from services.bot_status import BotStatusService
from states import Instruction, AdminSearchManagementSG
from tasks import task_manager


class IsAdmin(Filter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return callback.from_user.id in ADMIN_ID


router = Router(name="admin_handlers")


async def toggle_notifications(callback: CallbackQuery, button, manager) -> None:
    """Обработчик переключения статуса уведомлений."""
    if not callback.from_user or callback.from_user.id not in ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # Переключаем статус уведомлений
    if task_manager.is_notifications_enabled():
        task_manager.disable_notifications()
        await callback.answer("🔕 Уведомления выключены", show_alert=True)
    else:
        task_manager.enable_notifications()
        await callback.answer("🔔 Уведомления включены", show_alert=True)

    # Перезапускаем диалог для обновления статуса
    try:
        from states import AdminManager
        await manager.done()
        await manager.start(AdminManager.dashboard, mode=StartMode.RESET_STACK)
    except Exception as e:
        logger.error("Ошибка при обновлении dashboard", error=str(e))


@router.callback_query(F.data == "trial_key")
async def on_trial_key(callback: CallbackQuery, dialog_manager: DialogManager):
    """Обработчик нажатия кнопки 'Активировать пробный период' в приветственном сообщении."""
    await callback.answer()
    await dialog_manager.start(Instruction.choosing_device, mode=StartMode.RESET_STACK)


@router.message(Command("search"))
async def cmd_search_user(message: Message, dialog_manager: DialogManager):
    """
    Обработчик команды /search для администраторов.

    Использование: /search <tg_id>
    Выводит информацию о пользователе, аналогично поиску через админ-панель.
    """
    if not message.from_user:
        return

    # Проверяем, что администратор
    if message.from_user.id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам")
        return

    # Парсим аргумент команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /search <tg_id>\n\n"
            "Пример: /search 123456789"
        )
        return

    try:
        search_tg_id = int(args[1])
    except ValueError:
        await message.answer("❌ TG ID должен быть числом")
        return

    logger.info(
        "Администратор использует команду /search",
        admin_id=message.from_user.id,
        target_tg_id=search_tg_id,
    )

    # Запускаем диалог отображения профиля пользователя
    await dialog_manager.start(
        AdminSearchManagementSG.profile_user,
        mode=StartMode.RESET_STACK,
        data={"tg_id": search_tg_id},
    )


@router.message(Command("status"))
async def cmd_status(message: Message, **data):
    """Отображает статус основных систем бота. Только для администраторов."""
    if not message.from_user or message.from_user.id not in ADMIN_ID:
        return

    cache = data.get("cache")
    xui_session = data.get("xui_session")
    session = data.get("session")

    text = await BotStatusService.build_status(
        task_manager=task_manager,
        # cache_storage: прямой доступ допустим — только чтение размеров namespace,
        # CacheService API не предоставляет метод подсчёта элементов
        cache_storage=cache.storage if cache else None,
        cache_service=cache,
        xui_session=xui_session,
        db_conn=session,
    )
    await message.answer(text, parse_mode="HTML")
