"""Фоновые рабочие функции для администраторских задач."""

from datetime import datetime, timezone
from typing import Optional

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from api.backend_client import BackendAPIClient
from logger import logger


async def delete_expired_keys_fast(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    """Удаляет просроченные ключи через Backend API."""
    try:
        container = manager.middleware_data.get("container")
        backend = container.resolve(BackendAPIClient) if container else None

        if not backend:
            await callback.answer(
                "❌ Ошибка: не удалось получить доступ к backend", show_alert=True
            )
            return

        all_keys = await backend.admin_list_keys()

        current_time = datetime.now(timezone.utc)
        current_timestamp_ms = int(current_time.timestamp() * 1000)

        expired_keys = [
            key
            for key in all_keys
            if key.expiry_time < current_timestamp_ms
        ]

        deleted_count = 0
        errors = []

        for key in expired_keys:
            try:
                success = await backend.admin_delete_key(key.email)
                if success:
                    deleted_count += 1
                else:
                    errors.append(f"Failed to delete {key.email}")
            except Exception as e:
                logger.error(
                    "Ошибка при удалении просроченного ключа",
                    email=key.email,
                    error=str(e),
                    exc_info=True,
                )
                errors.append(str(e))

        if deleted_count > 0:
            logger.info(
                "Просроченные ключи удалены",
                deleted_count=deleted_count,
                total_expired=len(expired_keys),
            )

        error_text = f"\n❌ Ошибок: {len(errors)}" if errors else ""
        await callback.answer(
            f"✅ Удалено просроченных ключей: {deleted_count}{error_text}",
            show_alert=True,
        )

        await manager.switch_to(manager.current_context().state)

    except Exception as e:
        logger.error(
            "Критическая ошибка при удалении просроченных ключей",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        await callback.answer(
            f"❌ Критическая ошибка: {str(e)}",
            show_alert=True,
        )
