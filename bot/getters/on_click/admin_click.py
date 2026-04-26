import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Radio

from bot_project import bot
from logger import logger
from services.cache.service import CacheService
from states.admin import AdminManager, AdminMassMailing


async def on_click_export_csv_handler(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик для экспорта CSV"""
    session = manager.middleware_data.get("session")

    # Ваша логика создания CSV
    query = """
        SELECT 
            u.tg_id, 
            u.username, 
            u.first_name, 
            u.last_name, 
            p.amount, 
            p.status,
            p.created_at,
            p.payment_type
        FROM users u
        JOIN payments p ON u.tg_id = p.tg_id
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="user_stats"))
    headers = (
        "tg_id,username,first_name,last_name,amount,status,created_at,payment_type"
    )
    data = await session.fetch(query)

    if not data:
        await callback.answer("📭 Нет данных для экспорта", show_alert=True)
        return

    # Создаем CSV данные
    csv_data = headers + "\n"
    for row in data:
        formatted_row = [
            f'"{str(value)}"' if "," in str(value) else str(value)
            for value in row.values()
        ]
        csv_data += ",".join(formatted_row) + "\n"

    # Создаем и отправляем файл
    csv_file = BufferedInputFile(
        csv_data.encode("utf-8-sig"), filename="payments_export.csv"
    )

    await callback.message.answer_document(
        csv_file,
        caption="📊 Экспорт платежей\nФайл содержит все данные о платежах",
        reply_markup=builder.as_markup(),
    )


async def on_click_restore_trial(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Кликер восстановления триального периода с проверкой кеша"""
    from services.cache.key_manager import CacheKeyManager
    from services.core.user.utils.trial import TrialService
    import punq

    # Получаем tg_id
    tg_id = (
        dialog_manager.dialog_data.get("tg_id")
        if dialog_manager.dialog_data
        else dialog_manager.start_data.get("tg_id")
    )

    if not tg_id:
        await callback.answer("❌ Пользователь не указан", show_alert=True)
        return

    # Проверяем наличие пользователя в кеше
    cache_service: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
    if not cache_service:
        await callback.answer(
            "❌ Ошибка: не удалось получить доступ к кешу", show_alert=True
        )
        return

    cache_key = CacheKeyManager.user(tg_id)
    user = await cache_service.users.get(cache_key)

    if not user:
        await callback.answer(
            f"❌ Пользователь {tg_id} не найден в системе", show_alert=True
        )
        logger.warning(
            "Попытка восстановить пробник несуществующему пользователю", tg_id=tg_id
        )
        return

    # Получаем TrialService из DI контейнера
    container: punq.Container = dialog_manager.middleware_data.get("container")
    if not container:
        await callback.answer(
            "❌ Ошибка: не удалось получить DI контейнер", show_alert=True
        )
        return

    try:
        trial_service: TrialService = container.resolve(TrialService)
        conn = dialog_manager.middleware_data.get("session")

        # trial=0 означает "пробный период доступен", trial=1 — "использован"
        updated_user = await trial_service.installation_trial(tg_id, conn, trial=0)

        if updated_user:
            # Обновляем пользователя в кеше
            await cache_service.users.set(cache_key, updated_user)
            logger.info("Trial period восстановлен для пользователя", tg_id=tg_id)
            await callback.answer(
                f"✅ Trial period успешно восстановлен для пользователя {tg_id}",
                show_alert=True,
            )
        else:
            await callback.answer(
                "❌ Ошибка при восстановлении trial period", show_alert=True
            )
    except Exception as e:
        logger.error(
            "Ошибка при восстановлении trial period", tg_id=tg_id, error=str(e)
        )
        await callback.answer(
            f"❌ Ошибка при восстановлении trial period: {str(e)}", show_alert=True
        )
        return


async def pin_message_in_chat(
    bot: Bot, chat_id: int, message_id: int, disable_notification: bool = False
):
    """
    Закрепляет сообщение в указанном чате.

    :param bot: Экземпляр Bot
    :param chat_id: ID чата
    :param message_id: ID сообщения, которое нужно закрепить
    :param disable_notification: Отправить без уведомления (по умолчанию False)
    """
    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        )
        logger.info("Сообщение закреплено", chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(
            "Не удалось закрепить сообщение",
            chat_id=chat_id,
            message_id=message_id,
            error=str(e),
        )


async def pin_last_message(
    bot: Bot,
    chat_id: int,
    text: str,
    disable_notification: bool = False,
    pin_mode: int = 2,
) -> int | None:
    """
    Отправляет сообщение и сразу закрепляет его.

    :param bot: Экземпляр Bot
    :param chat_id: ID чата
    :param text: Текст сообщения
    :param disable_notification: Отправлять без уведомления
    :return: ID сообщения, если успешно
    """
    try:
        message = await bot.send_message(chat_id, text, parse_mode="HTML")
        if pin_mode == 1:
            await pin_message_in_chat(
                bot, chat_id, message.message_id, disable_notification
            )
        return message.message_id
    except Exception as e:
        logger.error(
            "Не удалось отправить и закрепить сообщение", chat_id=chat_id, error=str(e)
        )
        return None


async def on_click_delete_user(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Кликер удаляет пользователя с проверкой кеша"""
    from services.cache.key_manager import CacheKeyManager
    from services.core.user.utils.delete_data import DeleteUser
    import punq

    # Получаем tg_id
    dialog_data = (
        dialog_manager.dialog_data
        if isinstance(dialog_manager.dialog_data, dict)
        else {}
    )
    start_data = (
        dialog_manager.start_data if isinstance(dialog_manager.start_data, dict) else {}
    )
    tg_id = dialog_data.get("tg_id") or start_data.get("tg_id")

    if not tg_id:
        await callback.answer("❌ Пользователь не указан", show_alert=True)
        return

    # Проверяем наличие пользователя в кеше
    cache_service: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
    if not cache_service:
        await callback.answer(
            "❌ Ошибка: не удалось получить доступ к кешу", show_alert=True
        )
        return

    cache_key = CacheKeyManager.user(tg_id)
    user = await cache_service.users.get(cache_key)

    if not user:
        await callback.answer(
            f"❌ Пользователь {tg_id} не найден в системе", show_alert=True
        )
        logger.warning("Попытка удалить несуществующего пользователя", tg_id=tg_id)
        return

    # Получаем DeleteUser из DI контейнера
    container: punq.Container = dialog_manager.middleware_data.get("container")
    if not container:
        await callback.answer(
            "❌ Ошибка: не удалось получить DI контейнер", show_alert=True
        )
        return

    try:
        delete_service: DeleteUser = container.resolve(DeleteUser)
        await delete_service.delete(tg_id)

        # Удаляем пользователя из кеша
        await cache_service.users.delete(cache_key)
        logger.info("Пользователь удалён из системы", tg_id=tg_id)

        await callback.answer(
            f"✅ Пользователь {tg_id} успешно удален из системы", show_alert=True
        )
    except Exception as e:
        logger.error("Ошибка при удалении пользователя", tg_id=tg_id, error=str(e))
        await callback.answer(
            f"❌ Ошибка при удалении пользователя: {str(e)}", show_alert=True
        )
        return

    await dialog_manager.start(AdminManager.main)


async def on_click_confirmation_of_sending(
    message, widget, dialog_manager: DialogManager, text: str
):
    """Подтверждение отправки сообщения"""
    dialog_manager.dialog_data["text"] = text
    await dialog_manager.switch_to(AdminMassMailing.confirmation)


async def on_click_mass_mailing(
    callback: CallbackQuery, _widgets: Button, dialog_manager: DialogManager
):
    """Кликер для приёма сообщения для массовой публикации"""

    cache_service: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
    selected_pin_mode = dialog_manager.dialog_data.get("pin_message")
    text_message = dialog_manager.dialog_data.get("text")
    logger.info(
        "Начинаю массовую рассылку", text=text_message, pin_mode=selected_pin_mode
    )

    if not cache_service:
        await callback.answer(
            "❌ Ошибка: не удалось получить доступ к кешу", show_alert=True
        )
        return

    users = await cache_service.users.all()
    if not isinstance(users, list):
        users = [users] if users else []

    tg_ids = [u.tg_id for u in users]
    total_users = len(tg_ids)
    semaphore = asyncio.Semaphore(50)

    async def send_with_semaphore(tg_id: int):
        async with semaphore:
            return await pin_last_message(
                bot,
                tg_id,
                text_message,
                disable_notification=True,
                pin_mode=selected_pin_mode,
            )

    tasks_send_message = [send_with_semaphore(tg_id) for tg_id in tg_ids]
    results = await asyncio.gather(*tasks_send_message)

    success_count = sum(1 for result in results if result is True)
    error_count = total_users - success_count
    await callback.answer(
        text=f"📤 Рассылка завершена:\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Не доставлено: {error_count}",
        show_alert=True,
    )
    await dialog_manager.done()


async def click_sync_cache(
    callback: CallbackQuery, widget: Button, dialog_manager: DialogManager, **kwargs
):
    """Синхронизация БД с кэшем через DatabaseSynchronizer"""
    from typing import Any
    import asyncpg
    import punq

    try:
        # Получаем зависимости из middleware
        container: Any = dialog_manager.middleware_data.get("container")
        if not isinstance(container, punq.Container):
            await callback.answer(
                "❌ Ошибка: не удалось получить DI контейнер", show_alert=True
            )
            return

        # Получаем необходимые сервисы из контейнера
        from services.core.data.service import ServiceDataModel
        from client import XUISession
        from services.synchron.database_synchronizer import DatabaseSynchronizer
        from services.synchron.xui_fetcher import XUIFetcher
        from services.synchron.cache_comparator import CacheComparator
        from services.synchron.key_creator import KeyCreator
        from services.synchron.tariff_matcher import TariffMatcher
        from services.synchron.traffic import TrafficUpdater

        model_data: ServiceDataModel = container.resolve(ServiceDataModel)
        pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
        xui_session: XUISession = container.resolve(XUISession)

        # Создаём экземпляр DatabaseSynchronizer
        tariff_matcher = TariffMatcher(model_data)
        synchronizer = DatabaseSynchronizer(
            xui_fetcher=XUIFetcher(),
            cache_comparator=CacheComparator(),
            key_creator=KeyCreator(model_data, pool, tariff_matcher),
            traffic_updater=TrafficUpdater(model_data),
            model_data=model_data,
            pool=pool,
        )

        # Выполняем синхронизацию
        async with synchronizer:
            stats = await synchronizer.sync_data(xui_session)

        panel_clients = stats.get("panel_clients", 0)
        total = stats.get("total", 0)
        successful = stats.get("successful", 0)
        failed = stats.get("failed", 0)
        missing_keys = stats.get("missing_keys", 0)
        missing_users = stats.get("missing_users", 0)
        restored_keys = stats.get("restored_keys", 0)
        restored_users = stats.get("restored_users", 0)

        logger.info(
            "Синхронизация завершена",
            panel_clients=panel_clients,
            total=total,
            successful=successful,
            failed=failed,
            restored_keys=restored_keys,
            restored_users=restored_users,
        )

        lines = [
            "Синхронизация завершена",
            f"Клиентов на панели: {panel_clients}",
            f"Трафик обновлён: {successful}/{total}",
        ]
        if missing_keys or missing_users:
            lines.append(
                f"Восстановлено: {restored_keys} ключей, {restored_users} пользователей"
            )
        if failed:
            lines.append(f"Ошибок: {failed}")

        await callback.answer(text="\n".join(lines), show_alert=True)

    except Exception as e:
        logger.error("Ошибка при синхронизации БД с кэшем", error=str(e))
        await callback.answer(f"❌ Ошибка синхронизации: {str(e)}", show_alert=True)


def validate_telegram_url(url: str) -> tuple[str, str]:
    """
    Расширенная валидация URL для Telegram

    Returns:
        tuple: (valid_url, error_message)
    """
    if not url:
        return "", "URL не может быть пустым"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        # Проверка порта
        if parsed.port is not None:
            if parsed.port < 1 or parsed.port > 65535:
                return (
                    "",
                    f"Некорректный порт: {parsed.port}. Допустимый диапазон: 1-65535",
                )
        # Проверка схемы
        allowed_schemes = ["http", "https", "ftp", "ftps"]
        if parsed.scheme and parsed.scheme not in allowed_schemes:
            return (
                "",
                f"Неподдерживаемая схема: {parsed.scheme}. Допустимые: {', '.join(allowed_schemes)}",
            )
        # Проверка хоста
        if not parsed.netloc:
            return "", "Отсутствует домен или хост"
        # Проверка длины
        if len(url) > 2048:
            return "", f"URL слишком длинный: {len(url)} символов (максимум 2048)"
        # Специфичные проверки для нестандартных URL
        if "v2raytun://" in url or "://import/" in url:
            return "", "Неподдерживаемый формат URL (v2raytun)"

        return url, ""
    except Exception as e:
        return "", f"Ошибка парсинга URL: {str(e)}"


async def on_click_url_test(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Получает ссылку из TextInput с улучшенной валидацией"""
    valid_url, error_message = validate_telegram_url(text)

    if not valid_url:
        await message.answer(
            f"❌ {error_message}\n\n"
            f"💡 Введите корректную HTTP/HTTPS ссылку:\n"
            f"• https://example.com\n"
            f"• http://mysite.org:8080\n"
            f"• example.com/path"
        )
        return

    # Сохраняем валидную ссылку
    dialog_manager.dialog_data["url"] = valid_url
    dialog_manager.dialog_data["original_input"] = (
        text  # Сохраняем оригинальный ввод для отображения
    )

    await dialog_manager.switch_to(AdminManager.test_key)


async def on_click_change_status(
    callback: CallbackQuery,
    widget: Radio,
    dialog_manager: DialogManager,
    item_id: int,
):
    """Запоминает выбранный статус рассылки"""
    dialog_manager.dialog_data["pin_message"] = int(item_id)
