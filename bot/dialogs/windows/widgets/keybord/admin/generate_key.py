"""KeyboardBuilder для админ-диалога генерации ключа."""

from typing import Optional

import asyncpg

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import (
    Column,
    Group,
    Radio,
    Button,
    Cancel,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from getters.on_click.admin_generate_key import on_tg_id_entered, error_gen_tg_id
from models import Inbound
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.keys.utils.create_key import CreateKey
from services.core.user.utils.saver import SeverUser
from states.admin import AdminManager, AdminGenerateKeySG
from logger import logger


class GenKeyInputTgIdKeyboard(KeyboardBuilder):
    """Клавиатура ввода tg_id для генерации ключа."""

    def build(self):
        return (
            TextInput(
                id="gen_key_tg_id",
                type_factory=int,
                on_success=on_tg_id_entered,
                on_error=error_gen_tg_id,
            ),
            Cancel(Const("🔙 Назад")),
        )  # type: ignore


class GenKeyChooseInboundKeyboard(KeyboardBuilder):
    """Клавиатура выбора inbound для генерации ключа."""

    def build(self):
        return (
            Group(
                Radio(
                    checked_text=Format("✅ {item.name_inbound}"),
                    unchecked_text=Format("⚪️ {item.name_inbound}"),
                    id="gen_inbound_radio",
                    item_id_getter=lambda inbound: str(inbound.inbound_id),
                    items="inbounds",
                ),
                width=3,
            ),
            SwitchTo(
                Const("➡️ Далее"),
                id="gen_key_next",
                state=AdminGenerateKeySG.choosing_tariff,
            ),
            Cancel(Const("🔙 Отмена")),
        )


class GenKeyChooseTariffKeyboard(KeyboardBuilder):
    """Клавиатура выбора тарифа для генерации ключа."""

    def build(self):
        return (
            Group(
                Radio(
                    checked_text=Format("✅ {item.name_tariff} — {item.amount}₽"),
                    unchecked_text=Format("⚪️ {item.name_tariff} — {item.amount}₽"),
                    id="gen_tariff_radio",
                    item_id_getter=lambda tariff: str(tariff.id),
                    items="tariffs",
                ),
                width=2,
            ),
            SwitchTo(
                Const("➡️ Далее"),
                id="gen_key_to_confirm",
                state=AdminGenerateKeySG.confirm_generate,
            ),
            SwitchTo(
                Const("🔙 Назад"),
                id="gen_key_back_to_inbound",
                state=AdminGenerateKeySG.choosing_inbound,
            ),
            Cancel(Const("❌ Отмена")),
        )


class GenKeyConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения генерации ключа."""

    async def _on_generate(
        self, callback: CallbackQuery, button, dialog_manager: DialogManager, **kwargs
    ):
        """Обработчик генерации ключа."""
        try:
            tg_id = dialog_manager.dialog_data.get("tg_id")
            user_exists = dialog_manager.dialog_data.get("user_exists", False)

            if not tg_id:
                await callback.answer("❌ ID пользователя не найден", show_alert=True)
                return

            container = dialog_manager.middleware_data.get("container")
            cache: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
            pool = container.resolve(asyncpg.Pool)

            if not all([container, cache, pool]):
                await callback.answer(
                    "❌ Ошибка: не удалось получить сервисы", show_alert=True
                )
                return

            # Получаем выбранный inbound
            widget_data = dialog_manager.current_context().widget_data
            selected_inbound_id = widget_data.get("gen_inbound_radio")
            if not selected_inbound_id:
                await callback.answer(
                    "❌ Пожалуйста, выберите подключение", show_alert=True
                )
                return

            all_inbounds = await cache.inbounds.all()
            if not isinstance(all_inbounds, list):
                all_inbounds = [all_inbounds] if all_inbounds else []

            selected_inbound: Optional[Inbound] = None
            for inbound in all_inbounds:
                if isinstance(inbound, Inbound) and str(inbound.inbound_id) == str(
                    selected_inbound_id
                ):
                    selected_inbound = inbound
                    break

            if not selected_inbound:
                await callback.answer(
                    "❌ Выбранное подключение не найдено", show_alert=True
                )
                return

            server_id = selected_inbound.server_id

            # Получаем выбранный тариф
            selected_tariff_id = widget_data.get("gen_tariff_radio")
            if not selected_tariff_id:
                await callback.answer("❌ Пожалуйста, выберите тариф", show_alert=True)
                return

            tariff_cache_key = CacheKeyManager.tariff(int(selected_tariff_id))
            tariff = await cache.tariffs.get(tariff_cache_key)

            if not tariff:
                await callback.answer("❌ Тариф не найден в кеше", show_alert=True)
                return

            # Если пользователь не существует — создаём
            if not user_exists:
                saver = container.resolve(SeverUser)
                new_user = await saver.register_user(
                    pool, tg_id=tg_id, server_id=server_id
                )
                cache_key = CacheKeyManager.user(tg_id)
                await cache.users.set(cache_key, new_user)
                logger.info(
                    f"Пользователь {tg_id} создан админом при генерации ключа",
                    server_id=server_id,
                )

            # Сохраняем temporary_inbound для FormConnectionData
            await cache.users.set(
                CacheKeyManager.temporary_inbound(tg_id), str(selected_inbound_id)
            )

            # Генерируем ключ
            create_key = container.resolve(CreateKey)
            result = await create_key.proces(
                tg_id=tg_id,
                tariff=tariff,
                server_id=server_id,
                conn=pool,
            )

            if not result:
                await callback.answer("❌ Ошибка при создании ключа", show_alert=True)
                return

            # Сохраняем результат в dialog_data
            dialog_manager.dialog_data["result"] = result

            logger.info(
                "Админ успешно сгенерировал ключ",
                tg_id=tg_id,
                email=result.get("email"),
            )

            await dialog_manager.switch_to(AdminGenerateKeySG.result)

        except Exception as e:
            logger.error(
                "Ошибка при генерации ключа администратором",
                tg_id=dialog_manager.dialog_data.get("tg_id"),
                error=str(e),
                exc_info=True,
            )
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    def build(self):
        return Column(
            Button(
                Const("✅ Сгенерировать"),
                id="gen_key_confirm",
                on_click=self._on_generate,
            ),
            SwitchTo(
                Const("🔙 Назад"),
                id="gen_key_back_tariff",
                state=AdminGenerateKeySG.choosing_tariff,
            ),
            Cancel(Const("❌ Отмена")),
        )


class GenKeyResultKeyboard(KeyboardBuilder):
    """Клавиатура результата генерации ключа."""

    async def _on_back_panel(
        self, callback: CallbackQuery, button, dialog_manager: DialogManager, **kwargs
    ):
        """Возврат в панель администратора."""
        await dialog_manager.start(AdminManager.main, mode=StartMode.RESET_STACK)

    def build(self):
        return Column(
            Url(
                Const("🔗 Открыть ключ"),
                url=Format("{link_to_connect}"),
            ),
            Button(
                Const("🔙 В панель"),
                id="gen_key_back_panel",
                on_click=self._on_back_panel,
            ),
        )
