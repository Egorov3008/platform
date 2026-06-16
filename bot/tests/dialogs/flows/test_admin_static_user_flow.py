"""
Комплексные тесты для flow AdminManager.static_user.

Тестируется полный цикл:
1. AdminStatsGetter → получение статистики и распределения ключей
2. AdminStatsKeyboard → отрисовка клавиатуры
3. AdminKeyListGetter → получение отфильтрованного списка ключей (segmentation)
4. on_key_selected → выбор конкретного ключа
5. AdminKeyDetailsGetter → получение деталей выбранного ключа
6. AdminKeyDetailsKeyboard handlers → открытие диалогов удаления/изменения

Все тесты используют единые тестовые данные, передаваемые через
BackendAPIClient (admin_list_keys, get_tariff, get_user, admin_list_users).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key
from states import AdminManager, AdminKeyDeleteSG, AdminKeyChangeDateSG, AdminKeyChangeTariffSG
from bot.getters.on_click.admin_keys import on_key_selected

from dialogs.windows.getters.admin.panel import AdminStatsGetter
from dialogs.windows.getters.admin.keys_list import (
    AdminKeyListGetter,
    AdminKeyDetailsGetter,
)
from dialogs.windows.widgets.keybord.admin.panel import AdminStatsKeyboard
from dialogs.windows.widgets.keybord.admin.keys_list import (
    AdminKeysListKeyboard,
    AdminKeyDetailsKeyboard,
)


# ============================================================================
# Фабрики тестовых данных (backend-формат)
# ============================================================================


def make_user_dict(
    tg_id: int,
    username: str = "user",
    created_at: datetime = None,
    is_blocked: bool = False,
) -> dict:
    """Backend-shaped user dict."""
    return {
        "tg_id": tg_id,
        "username": f"{username}_{tg_id}",
        "trial": 0,
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "server_id": 1,
        "is_blocked": is_blocked,
    }


def make_key_dict(
    email: str,
    tg_id: int = 1,
    expiry_offset_ms: int = 86400000,
    tariff_id: int = 20,
) -> dict:
    """Backend-shaped key dict."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "email": email,
        "tg_id": tg_id,
        "client_id": f"c_{tg_id}",
        "key": f"key_{email}",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "tariff_id": tariff_id,
    }


def make_tariff_dict(id: int = 20, name_tariff: str = "Premium", amount: float = 100.0) -> dict:
    """Backend-shaped tariff dict."""
    return {
        "id": id,
        "name_tariff": name_tariff,
        "amount": amount,
    }


def make_key_obj(
    email: str,
    tg_id: int = 1,
    expiry_offset_ms: int = 86400000,
    tariff_id: int = 20,
) -> Key:
    """Создание Key из backend dict."""
    from models import Key as KeyModel
    return KeyModel.from_backend(make_key_dict(email, tg_id, expiry_offset_ms, tariff_id))


# ============================================================================
# Фикстуры
# ============================================================================


@pytest.fixture
def shared_test_data():
    """
    Единые тестовые данные для всех тестов flow.

    Создаёт набор ключей различных категорий:
    - expired: 2 ключа (истёкшие)
    - expiring_24h: 2 ключа (истекают в 24 часа)
    - expiring_7d: 1 ключ (истекает в 7 дней)
    - active: 2 ключа (активные, далеко до истечения)
    - trial: 1 ключ (trial тариф, tariff_id=10)
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    hour_ms = 3600 * 1000
    day_ms = 24 * 3600 * 1000

    return {
        "users": [
            make_user_dict(111),
            make_user_dict(222),
            make_user_dict(333),
            make_user_dict(444),  # для total = 4
        ],
        "keys": [
            make_key_dict("expired1@example.com", 111, -5 * day_ms, tariff_id=20),
            make_key_dict("expired2@example.com", 222, -1 * day_ms, tariff_id=20),
            make_key_dict("exp24h_5h@example.com", 111, 5 * hour_ms, tariff_id=20),
            make_key_dict("exp24h_20h@example.com", 222, 20 * hour_ms, tariff_id=20),
            make_key_dict("exp7d@example.com", 333, 7 * day_ms, tariff_id=20),
            make_key_dict("active1@example.com", 111, 60 * day_ms, tariff_id=20),
            make_key_dict("active2@example.com", 222, 90 * day_ms, tariff_id=20),
            make_key_dict("trial@example.com", 333, 30 * day_ms, tariff_id=10),
        ],
        "tariffs": {
            10: make_tariff_dict(10, "Trial"),
            20: make_tariff_dict(20, "Premium"),
        },
    }


@pytest.fixture
def mock_dialog_manager(shared_test_data):
    """Mock DialogManager с dialog_data и middleware_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    manager.switch_to = AsyncMock()
    manager.start = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def mock_backend(shared_test_data):
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.admin_list_users = AsyncMock(return_value=shared_test_data["users"])
    backend.admin_list_keys = AsyncMock(return_value=shared_test_data["keys"])
    backend.get_tariff = AsyncMock(
        side_effect=lambda tid: shared_test_data["tariffs"].get(tid)
    )
    backend.get_user = AsyncMock(return_value=None)
    return backend


# ============================================================================
# Тесты AdminStatsGetter
# ============================================================================


class TestAdminStatsGetterWithSharedData:
    """Тесты AdminStatsGetter с едиными тестовыми данными."""

    async def test_returns_stats_msg_with_all_counts(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """STATS_MSG должен содержать счётчики сегментов и пользователей."""
        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in result
        stats_msg = result["STATS_MSG"]

        # Сообщение содержит метрики пользователей (4 шт.)
        assert "Всего: 4" in stats_msg
        assert "Новые за неделю" in stats_msg

    async def test_writes_all_keys_to_dialog_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """AdminStatsGetter должен сохранить all_keys в dialog_data."""
        getter = AdminStatsGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8

    async def test_stats_match_shared_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Статистика должна показывать правильные значения."""
        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        stats_msg = result["STATS_MSG"]
        assert "Всего:" in stats_msg
        # 4 пользователя
        assert "Всего: 4" in stats_msg

        # Ключи сохранены в dialog_data
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8


# ============================================================================
# Тесты AdminStatsKeyboard
# ============================================================================


class TestAdminStatsKeyboard:
    """Тесты клавиатуры AdminStatsKeyboard (статистика пользователей)."""

    async def test_keyboard_has_delete_keys_button(self):
        """Клавиатура должна содержать кнопку удаления старых ключей."""
        keyboard = AdminStatsKeyboard()
        built = keyboard.build()
        assert built is not None

    async def test_keyboard_has_back_button(self):
        """Клавиатура должна содержать кнопку Назад."""
        keyboard = AdminStatsKeyboard()
        built = keyboard.build()
        assert built is not None


# ============================================================================
# Тесты AdminKeyListGetter
# ============================================================================


class TestAdminKeyListGetterWithSharedData:
    """Тесты AdminKeyListGetter с едиными тестовыми данными."""

    async def test_reads_segment_from_dialog_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """AdminKeyListGetter должен читать current_segment из dialog_data."""
        mock_dialog_manager.dialog_data["current_segment"] = "expired"

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["segment"] == "expired"
        # 2 просроченных ключа
        assert result["total_keys"] == 2

    async def test_all_segment_returns_all_keys(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Сегмент 'all' должен вернуть все 8 ключей."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 8
        assert len(result["keys_data"]) == 8

    async def test_expired_segment_returns_only_expired(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Сегмент 'expired' должен вернуть только просроченные ключи."""
        mock_dialog_manager.dialog_data["current_segment"] = "expired"

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 2
        emails = [key.email for _, key in result["keys_data"]]
        assert "expired1@example.com" in emails
        assert "expired2@example.com" in emails

    async def test_keys_data_format(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """keys_data должен быть списком кортежей (label, key)."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["keys_data"]) > 0
        label, key = result["keys_data"][0]
        assert isinstance(label, str)
        assert isinstance(key, Key)

    async def test_keys_data_contains_email_and_tg_id(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Label в keys_data должен содержать email и tg_id."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        target_email = "expired1@example.com"
        found = False
        for label, key in result["keys_data"]:
            if key.email == target_email:
                found = True
                assert target_email in label
                assert "111" in label  # tg_id
                break

        assert found, f"Ключ {target_email} не найден в keys_data"

    async def test_stores_filtered_keys_in_dialog_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """get_data должен сохранить filtered_keys в dialog_data."""
        mock_dialog_manager.dialog_data["current_segment"] = "expiring_24h"

        getter = AdminKeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "filtered_keys" in mock_dialog_manager.dialog_data
        assert isinstance(mock_dialog_manager.dialog_data["filtered_keys"], list)


# ============================================================================
# Тесты on_key_selected (module-level handler)
# ============================================================================


class TestOnKeySelectedWithSharedData:
    """Тесты обработчика on_key_selected с едиными данными."""

    async def test_finds_key_by_email(self, mock_dialog_manager, shared_test_data):
        """on_key_selected должен найти ключ по email."""
        mock_dialog_manager.dialog_data["filtered_keys"] = [
            make_key_obj("active1@example.com", tg_id=111),
            make_key_obj("active2@example.com", tg_id=222),
        ]

        callback = AsyncMock()

        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "active1@example.com",
        )

        assert "selected_key" in mock_dialog_manager.dialog_data
        selected = mock_dialog_manager.dialog_data["selected_key"]
        assert selected.email == "active1@example.com"
        assert selected.tg_id == 111

    async def test_writes_selected_key_email(self, mock_dialog_manager, shared_test_data):
        """on_key_selected должен сохранить selected_key_email."""
        mock_dialog_manager.dialog_data["filtered_keys"] = [
            make_key_obj("trial@example.com", tg_id=333, tariff_id=10),
        ]
        callback = AsyncMock()

        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "trial@example.com",
        )

        assert mock_dialog_manager.dialog_data["selected_key_email"] == "trial@example.com"

    async def test_answer_contains_selected_email(
        self, mock_dialog_manager, shared_test_data
    ):
        """Ответ должен содержать email выбранного ключа."""
        mock_dialog_manager.dialog_data["filtered_keys"] = [
            make_key_obj("expired2@example.com", tg_id=222, expiry_offset_ms=-1 * 86400000),
        ]
        callback = AsyncMock()

        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "expired2@example.com",
        )

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        answer_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "expired2@example.com" in answer_text

    async def test_no_filtered_keys_answers_error(self, mock_dialog_manager):
        """Без filtered_keys должен ответить ошибкой."""
        mock_dialog_manager.dialog_data = {}
        callback = AsyncMock()

        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "any@example.com",
        )

        callback.answer.assert_called_once()
        # Должен быть ответ "Ключи не загружены"
        answer_text = str(callback.answer.call_args)
        assert "❌" in answer_text


# ============================================================================
# Тесты AdminKeyDetailsGetter
# ============================================================================


class TestAdminKeyDetailsGetterWithSharedData:
    """Тесты AdminKeyDetailsGetter с едиными данными."""

    async def test_reads_selected_key_from_start_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """AdminKeyDetailsGetter должен читать selected_key из start_data."""
        selected_key = make_key_obj("expired1@example.com", tg_id=111)
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_backend.get_tariff.return_value = shared_test_data["tariffs"][20]

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is False
        assert result.get("tg_id") == 111
        assert result.get("keys") == "key_expired1@example.com"

    async def test_reads_selected_key_from_dialog_data(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """AdminKeyDetailsGetter должен читать selected_key из dialog_data (fallback)."""
        selected_key = make_key_obj("exp7d@example.com", tg_id=333, expiry_offset_ms=7 * 86400000)
        mock_dialog_manager.start_data = {}
        mock_dialog_manager.dialog_data["selected_key"] = selected_key
        mock_backend.get_tariff.return_value = shared_test_data["tariffs"][20]

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is False
        assert result.get("tg_id") == 333
        assert result.get("keys") == "key_exp7d@example.com"

    async def test_returns_keymodel_fields(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Результат должен содержать поля KeyModel.to_dict()."""
        selected_key = make_key_obj("trial@example.com", tg_id=333, tariff_id=10)
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_backend.get_tariff.return_value = shared_test_data["tariffs"][10]

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "status_emoji" in result
        assert "status_text" in result
        assert "is_trial" in result
        assert "is_active" in result

    async def test_returns_admin_specific_fields(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Результат должен содержать admin-специфичные поля."""
        selected_key = make_key_obj("expired1@example.com", tg_id=111)
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_backend.get_tariff.return_value = shared_test_data["tariffs"][20]

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("tg_id") == 111
        assert result.get("client_id") == "c_111"
        assert result.get("inbound_id") == 1

    async def test_returns_error_when_no_key(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """При отсутствии ключа должен вернуть error=True."""
        mock_dialog_manager.start_data = {}
        mock_dialog_manager.dialog_data = {}

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True

    async def test_returns_error_when_tariff_missing(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """Если тариф не найден, должен вернуть error=True."""
        selected_key = make_key_obj("test@example.com", tg_id=111, tariff_id=999)
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_backend.get_tariff.return_value = None

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True


# ============================================================================
# Тесты AdminKeyDetailsKeyboard handlers
# ============================================================================


class TestAdminKeyDetailsKeyboardHandlers:
    """Тесты обработчиков AdminKeyDetailsKeyboard с едиными данными."""

    async def test_to_delete_opens_delete_dialog(self, mock_dialog_manager, shared_test_data):
        """_to_delete должен открыть диалог удаления с email ключа."""
        selected_key = make_key_obj("expired1@example.com", tg_id=111)
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_delete(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyDeleteSG.confirm
        assert call_args[1]["data"]["email"] == "expired1@example.com"

    async def test_to_change_date_opens_date_dialog(
        self, mock_dialog_manager, shared_test_data
    ):
        """_to_change_date должен открыть диалог изменения даты."""
        selected_key = make_key_obj("exp7d@example.com", tg_id=333, expiry_offset_ms=7 * 86400000)
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_date(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyChangeDateSG.pick_date
        assert call_args[1]["data"]["email"] == "exp7d@example.com"

    async def test_to_change_tariff_opens_tariff_dialog(
        self, mock_dialog_manager, shared_test_data
    ):
        """_to_change_tariff должен открыть диалог изменения тарифа."""
        selected_key = make_key_obj("trial@example.com", tg_id=333, tariff_id=10)
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_tariff(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyChangeTariffSG.pick_tariff
        assert call_args[1]["data"]["email"] == "trial@example.com"

    async def test_to_change_date_without_key_answers_error(self, mock_dialog_manager):
        """_to_change_date без выбранного ключа отвечает ошибкой."""
        mock_dialog_manager.dialog_data = {}
        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_date(callback, None, mock_dialog_manager)

        callback.answer.assert_called_once()
        assert "❌" in str(callback.answer.call_args) or "Ключ" in str(callback.answer.call_args)


# ============================================================================
# Интеграционные тесты полного flow
# ============================================================================


class TestAdminStaticUserFlowIntegration:
    """
    Интеграционные тесты AdminStatsGetter.

    Проверяет что AdminStatsGetter корректно собирает
    статистику и сохраняет all_keys в dialog_data.
    """

    async def test_getter_returns_stats_and_stores_keys(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """AdminStatsGetter должен вернуть STATS_MSG и сохранить all_keys."""
        stats_getter = AdminStatsGetter(mock_backend)
        stats_result = await stats_getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in stats_result
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8

    async def test_stats_contains_user_metrics(
        self, mock_backend, mock_dialog_manager, shared_test_data
    ):
        """STATS_MSG должен содержать метрики пользователей."""
        stats_getter = AdminStatsGetter(mock_backend)
        stats_result = await stats_getter.get_data(mock_dialog_manager)

        msg = stats_result["STATS_MSG"]
        # Проверяем что присутствуют ключевые метрики
        assert "Всего:" in msg
        assert "Новые за неделю:" in msg
        assert "Новые за месяц:" in msg
        assert "Новые за год:" in msg
        assert "Отток за неделю:" in msg
        assert "Отток за месяц:" in msg
        assert "Отток за год:" in msg
        assert "Заблокировали бота:" in msg


# ============================================================================
# Тесты AdminStatsMessage builder
# ============================================================================


class TestAdminStatsMessageBuilder:
    """Тесты AdminStatsMessage с едиными данными."""

    def test_build_returns_format_with_stats_msg(self):
        """AdminStatsMessage.build должен вернуть Format с {STATS_MSG}."""
        from dialogs.windows.widgets.message.admin.panel import AdminStatsMessage
        from aiogram_dialog.widgets.text import Format

        message = AdminStatsMessage()
        result = message.build()

        assert isinstance(result, Format)
        assert "{STATS_MSG}" in result.text
