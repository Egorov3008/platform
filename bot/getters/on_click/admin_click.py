import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Radio

from api.backend_client import BackendAPIClient
from bot_project import bot
from logger import logger
from states.admin import AdminManager, AdminMassMailing


async def on_click_export_csv_handler(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик для экспорта CSV через Backend API."""
    container = manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    if not backend:
        await callback.answer("❌ Backend недоступен", show_alert=True)
        return

    users = await backend.admin_list_users()
    payments = await backend.admin_list_payments()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="user_stats"))
    headers = (
        "tg_id,username,first_name,last_name,amount,status,created_at,payment_type"
    )

    if not users or not payments:
        await callback.answer("📭 Нет данных для экспорта", show_alert=True)
        return

    # Create a map of tg_id -> user info
    user_map = {u.get("tg_id"): u for u in users}

    csv_data = headers + "\n"
    for p in payments:
        u = user_map.get(p.get("tg_id"), {})
        row = [
            str(p.get("tg_id", "")),
            u.get("username", ""),
            u.get("first_name", ""),
            u.get("last_name", ""),
            str(p.get("amount", "")),
            p.get("status", ""),
            str(p.get("created_at", "")),
            p.get("payment_type", ""),
        ]
        formatted_row = [
            f'"{str(value)}"' if "," in str(value) else str(value)
            for value in row
        ]
        csv_data += ",".join(formatted_row) + "\n"

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
    """Кликер восстановления триального периода через Backend API."""
    tg_id = (
        dialog_manager.dialog_data.get("tg_id")
        if dialog_manager.dialog_data
        else dialog_manager.start_data.get("tg_id")
    )

    if not tg_id:
        await callback.answer("❌ Пользователь не указан", show_alert=True)
        return

    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    if not backend:
        await callback.answer("❌ Backend недоступен", show_alert=True)
        return

    user = await backend.get_user(tg_id)
    if not user:
        await callback.answer(
            f"❌ Пользователь {tg_id} не найден в системе", show_alert=True
        )
        return

    try:
        updated = await backend.admin_update_user(tg_id, {"trial": 0})
        if updated:
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


async def pin_message_in_chat(
    bot: Bot, chat_id: int, message_id: int, disable_notification: bool = False
):
    """Закрепляет сообщение в указанном чате."""
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
    """Отправляет сообщение и сразу закрепляет его."""
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
    """Кликер удаляет пользователя через Backend API."""
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

    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    if not backend:
        await callback.answer("❌ Backend недоступен", show_alert=True)
        return

    user = await backend.get_user(tg_id)
    if not user:
        await callback.answer(
            f"❌ Пользователь {tg_id} не найден в системе", show_alert=True
        )
        return

    try:
        success = await backend.admin_delete_user(tg_id)
        if success:
            logger.info("Пользователь удалён из системы", tg_id=tg_id)
            await callback.answer(
                f"✅ Пользователь {tg_id} успешно удален из системы", show_alert=True
            )
        else:
            await callback.answer(
                f"❌ Ошибка при удалении пользователя {tg_id}", show_alert=True
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
    """Подтверждение отправки сообщения."""
    dialog_manager.dialog_data["text"] = text
    await dialog_manager.switch_to(AdminMassMailing.confirmation)


async def on_click_mass_mailing(
    callback: CallbackQuery, _widgets: Button, dialog_manager: DialogManager
):
    """Кликер для приёма сообщения для массовой публикации через Backend API."""
    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    selected_pin_mode = dialog_manager.dialog_data.get("pin_message")
    text_message = dialog_manager.dialog_data.get("text")
    logger.info(
        "Начинаю массовую рассылку", text=text_message, pin_mode=selected_pin_mode
    )

    if not backend:
        await callback.answer(
            "❌ Ошибка: не удалось получить доступ к backend", show_alert=True
        )
        return

    users = await backend.admin_list_users()
    if not isinstance(users, list):
        users = [users] if users else []

    tg_ids = [u.get("tg_id") for u in users if u.get("tg_id")]
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

    success_count = sum(1 for result in results if result is not None)
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
    """Trigger manual cache and panel synchronization via Backend API."""
    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    if not backend:
        await callback.answer("❌ Backend недоступен", show_alert=True)
        return

    await callback.answer("🔄 Запуск синхронизации…", show_alert=False)

    try:
        result = await backend.admin_sync()
    except Exception as e:
        logger.error("Ошибка при вызове admin_sync", error=str(e))
        await callback.message.answer("❌ Ошибка синхронизации. Подробности в логах.")
        return

    if result.get("status") != "success":
        error_detail = result.get("detail") or result.get("error") or str(result)
        await callback.message.answer(
            f"❌ Синхронизация завершилась с ошибкой:\n<code>{error_detail}</code>",
            parse_mode="HTML",
        )
        return

    panel = result.get("panel", {})
    cache = result.get("cache", {})

    traffic_ok = panel.get("traffic_updated", 0)
    traffic_fail = panel.get("traffic_failed", 0)
    traffic_total = traffic_ok + traffic_fail

    lines = [
        "✅ <b>Синхронизация завершена</b>",
        "",
        f"📦 <b>Кэш:</b> {cache.get('message', '—')}",
        "",
        "📊 <b>Панель:</b>",
        f"• Клиентов на панели: {panel.get('panel_clients', 0)}",
        f"• Ключей в БД: {panel.get('db_keys_before', 0)} → {panel.get('db_keys_after', 0)}",
        f"• Совпадений: {panel.get('synced', 0)}, обновлено панель: {panel.get('panel_updated', 0)}, обновлено БД: {panel.get('db_updated', 0)}",
        f"• Создано: {panel.get('created', 0)}, удалено orphaned: {panel.get('orphaned_deleted', 0)}",
        f"• Трафик обновлён: {traffic_ok} / {traffic_total}",
    ]

    await callback.message.answer("\n".join(lines), parse_mode="HTML")


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
        if parsed.port is not None:
            if parsed.port < 1 or parsed.port > 65535:
                return (
                    "",
                    f"Некорректный порт: {parsed.port}. Допустимый диапазон: 1-65535",
                )
        allowed_schemes = ["http", "https", "ftp", "ftps"]
        if parsed.scheme and parsed.scheme not in allowed_schemes:
            return (
                "",
                f"Неподдерживаемая схема: {parsed.scheme}. Допустимые: {', '.join(allowed_schemes)}",
            )
        if not parsed.netloc:
            return "", "Отсутствует домен или хост"
        if len(url) > 2048:
            return "", f"URL слишком длинный: {len(url)} символов (максимум 2048)"
        if "v2raytun://" in url or "://import/" in url:
            return "", "Неподдерживаемый формат URL (v2raytun)"

        return url, ""
    except Exception as e:
        return "", f"Ошибка парсинга URL: {str(e)}"


async def on_click_url_test(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Получает ссылку из TextInput с улучшенной валидацией."""
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

    dialog_manager.dialog_data["url"] = valid_url
    dialog_manager.dialog_data["original_input"] = text

    await dialog_manager.switch_to(AdminManager.test_key)


async def on_click_change_status(
    callback: CallbackQuery,
    widget: Radio,
    dialog_manager: DialogManager,
    item_id: int,
):
    """Запоминает выбранный статус рассылки."""
    dialog_manager.dialog_data["pin_message"] = int(item_id)
