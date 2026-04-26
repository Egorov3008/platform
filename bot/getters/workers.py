"""Фоновые рабочие функции для администраторских задач."""

from datetime import datetime, timezone
from typing import Optional

import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from logger import logger
from services.cache.service import CacheService


async def delete_expired_keys_fast(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    """Удаляет просроченные ключи из БД и кеша.

    Функция получает ServiceDataModel через DI контейнер,
    находит все просроченные ключи и удаляет их из БД и кеша.
    """
    try:
        session: Optional[asyncpg.Connection] = manager.middleware_data.get("session")
        cache: Optional[CacheService] = manager.middleware_data.get("cache")

        if not session or not cache:
            await callback.answer(
                "❌ Ошибка: не удалось получить доступ к БД или кешу", show_alert=True
            )
            return

        # Получаем все ключи
        all_keys = await cache.keys.all()
        if not isinstance(all_keys, list):
            all_keys = [all_keys] if all_keys else []

        current_time = datetime.now(timezone.utc)
        current_timestamp_ms = int(current_time.timestamp() * 1000)

        # Находим просроченные ключи
        expired_keys = [
            key
            for key in all_keys
            if hasattr(key, "expiry_time") and key.expiry_time < current_timestamp_ms
        ]

        deleted_count = 0
        errors = []

        # Удаляем каждый просроченный ключ
        for key in expired_keys:
            try:
                # Удаляем из БД
                await session.execute(
                    "DELETE FROM keys WHERE email = $1",
                    key.email,
                )

                # Удаляем из кеша
                await cache.keys.delete(key.email)

                deleted_count += 1
            except Exception as e:
                logger.error(
                    "Ошибка при удалении просроченного ключа",
                    email=key.email if hasattr(key, "email") else "unknown",
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
