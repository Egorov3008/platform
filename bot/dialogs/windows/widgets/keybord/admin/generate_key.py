"""KeyboardBuilder для админ-диалога генерации ключа."""

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

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from getters.on_click.admin_generate_key import on_tg_id_entered, error_gen_tg_id
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
        """Обработчик генерации ключа через backend API."""
        try:
            tg_id = dialog_manager.dialog_data.get("tg_id")
            if not tg_id:
                await callback.answer("❌ ID пользователя не найден", show_alert=True)
                return

            container = dialog_manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Ошибка: не удалось получить сервисы", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)

            widget_data = dialog_manager.current_context().widget_data
            selected_inbound_id = widget_data.get("gen_inbound_radio")
            selected_tariff_id = widget_data.get("gen_tariff_radio")
            if not selected_tariff_id:
                await callback.answer("❌ Пожалуйста, выберите тариф", show_alert=True)
                return

            result = await backend.admin_generate_key(
                tg_id=tg_id,
                tariff_id=int(selected_tariff_id),
                inbound_id=int(selected_inbound_id) if selected_inbound_id else None,
            )

            if not result:
                await callback.answer("❌ Ошибка при создании ключа", show_alert=True)
                return

            dialog_manager.dialog_data["result"] = result
            logger.info("Админ сгенерировал ключ через backend", tg_id=tg_id, email=result.get("email"))
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
