from aiogram_dialog.widgets.kbd import Column, Start, SwitchTo, Button
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import AdminManager, AdminSearchManagementSG, AdminMassMailing, MainMenu, AdminGenerateKeySG, AdminUserCleanupSG, AdminMassRenewal


class AdminMainKeyboard(KeyboardBuilder):
    """Клавиатура главной панели администратора."""

    async def _on_sync_cache(self, callback, button, manager):
        """Обработчик синхронизации кеша и БД."""
        try:
            from getters.on_click.admin_click import click_sync_cache

            await click_sync_cache(callback, button, manager)
        except ImportError:
            await callback.answer("⚠️ Функция синхронизации недоступна", show_alert=True)

    def build(self):
        return Column(
            SwitchTo(
                Const("📊 Статистика пользователей"),
                id="user_stats",
                state=AdminManager.static_user,
            ),
            SwitchTo(
                Const("🔑 Статистика ключей"),
                id="key_stats",
                state=AdminManager.key_stats,
            ),
            SwitchTo(
                Const("💰 Статистика платежей"),
                id="payment_stats",
                state=AdminManager.payment_stats,
            ),
            SwitchTo(
                Const("📊 Dashboard"),
                id="dashboard",
                state=AdminManager.dashboard,
            ),
            Start(Const("👥 Поиск"), id="search", state=AdminSearchManagementSG.main),
            Start(
                Const("📢 Массовая рассылка"),
                id="send_to_alls",
                state=AdminMassMailing.receiving_message,
            ),
            Start(
                Const("🔑 Сгенерировать ключ"),
                id="generate_key",
                state=AdminGenerateKeySG.input_tg_id,
            ),
            Start(
                Const("📦 Массовое продление"),
                id="mass_renewal",
                state=AdminMassRenewal.select_segment,
            ),
            Button(
                Const("🔄 Синхронизация панели и БД"),
                id="synchronization",
                on_click=self._on_sync_cache,
            ),
            Start(Const("🔙 Назад"), id="back_profile", state=MainMenu.main),
        )


class AdminStatsKeyboard(KeyboardBuilder):
    """Клавиатура статистики пользователей."""

    def build(self):
        return Column(
            SwitchTo(
                Const("🗑️ Удалить старые ключи"),
                id="delete_keys",
                state=AdminManager.confirmation_deletion_keys,
            ),
            Start(
                Const("🧹 Удалить неактивных"),
                id="delete_inactive",
                state=AdminUserCleanupSG.review,
            ),
            SwitchTo(Const("🔙 Назад"), id="back_main", state=AdminManager.main),
        )
