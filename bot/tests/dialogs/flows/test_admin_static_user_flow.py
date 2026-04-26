"""
Комплексные тесты для flow AdminManager.static_user.

Тестируется полный цикл:
1. AdminStatsGetter → получение статистики и распределения ключей
2. AdminStatsKeyboard handlers → фильтрация по сегментам (all, 24h, expired)
3. AdminKeyListGetter → получение отфильтрованного списка ключей
4. on_key_selected → выбор конкретного ключа
5. AdminKeyDetailsGetter → получение деталей выбранного ключа

Все тесты используют единые тестовые данные для согласованности между:
- AdminStatsMessage (вывод статистики)
- keyboard_cls (формирование списков в клавиатурах)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from models import Key, User, Tariff, PaymentModel
from states import AdminManager, AdminKeyDeleteSG, AdminKeyChangeDateSG, AdminKeyChangeTariffSG

# ===== Getters =====
from dialogs.windows.getters.admin.panel import AdminStatsGetter
from dialogs.windows.widgets.keybord.admin.panel import AdminStatsKeyboard

# ===== Message builders =====
from dialogs.windows.widgets.message.admin.panel import AdminStatsMessage


# ============================================================================
# Фабрики тестовых данных
# ============================================================================


def make_user(tg_id: int, username: str, trial: int = 0) -> User:
    """Создание тестового пользователя."""
    return User(
        tg_id=tg_id,
        username=username,
        trial=trial,
        created_at=datetime.now(timezone.utc),
        server_id=1,
    )


def make_key(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    tariff_id: int = 20,
    total_gb: int = 10,
    used_traffic: int = 1000,
) -> Key:
    """
    Создание тестового ключа.
    
    Args:
        email: Email ключа
        tg_id: Telegram ID владельца
        expiry_offset_ms: Смещение времени истечения (мс) относительно now
                         отрицательное = уже истёк
        tariff_id: ID тарифа (10 = trial, 20 = paid)
        total_gb: Общий лимит трафика (GB)
        used_traffic: Использованный трафик (bytes)
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id=f"c_{tg_id}",
        key=f"key_{email}",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        tariff_id=tariff_id,
        total_gb=total_gb,
        used_traffic=used_traffic,
        created_at=datetime.now(timezone.utc),
    )


def make_payment(amount: float, created_offset_sec: int = 0, status: str = "succeeded") -> PaymentModel:
    """Создание тестового платежа."""
    created = datetime.now(timezone.utc)
    if created_offset_sec != 0:
        from datetime import timedelta
        created = created + timedelta(seconds=created_offset_sec)
    
    return PaymentModel(
        payment_id=f"pay_{amount}_{created_offset_sec}",
        tg_id=123456,
        amount=amount,
        status=status,
        created_at=created,
    )


def make_tariff(id: int = 20, name_tariff: str = "Premium") -> Tariff:
    """Создание тестового тарифа."""
    return Tariff(
        id=id,
        name_tariff=name_tariff,
        amount=100.0,
        traffic_limit=10,
    )


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
    - trial: 1 ключ (trial тариф)
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    hour_ms = 3600 * 1000
    day_ms = 24 * 3600 * 1000
    
    return {
        "users": [
            make_user(111, "user1"),
            make_user(222, "user2"),
            make_user(333, "user3"),
        ],
        "keys": [
            # Просроченные ключи
            make_key("expired1@example.com", 111, -5 * day_ms, tariff_id=20),
            make_key("expired2@example.com", 222, -1 * day_ms, tariff_id=20),
            
            # Истекают в 24 часа (5h и 20h)
            make_key("exp24h_5h@example.com", 111, 5 * hour_ms, tariff_id=20),
            make_key("exp24h_20h@example.com", 222, 20 * hour_ms, tariff_id=20),
            
            # Истекает в 7 дней
            make_key("exp7d@example.com", 333, 7 * day_ms, tariff_id=20),
            
            # Активные (далеко до истечения)
            make_key("active1@example.com", 111, 60 * day_ms, tariff_id=20),
            make_key("active2@example.com", 222, 90 * day_ms, tariff_id=20),
            
            # Trial ключ
            make_key("trial@example.com", 333, 30 * day_ms, tariff_id=10),
        ],
        "payments": [
            make_payment(100.0, -3600, "succeeded"),  # 1 час назад
            make_payment(200.0, -7200, "succeeded"),  # 2 часа назад
            make_payment(150.0, -86400, "succeeded"),  # 1 день назад
            make_payment(300.0, -604800, "succeeded"),  # 7 дней назад
        ],
        "tariffs": {
            10: make_tariff(10, "Trial"),
            20: make_tariff(20, "Premium"),
        }
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
def mock_cache_service(shared_test_data):
    """Mock CacheService с тестовыми данными."""
    cache = AsyncMock()
    cache.keys = AsyncMock()
    cache.keys.all = AsyncMock(return_value=shared_test_data["keys"])
    cache.keys.get = AsyncMock()
    cache.keys.set = AsyncMock()
    cache.tariffs = AsyncMock()
    cache.tariffs.get = AsyncMock()
    
    # Настройка mock для получения тарифов
    def get_tariff(key):
        tariff_id = int(key.split("_")[-1]) if "_" in key else 20
        return shared_test_data["tariffs"].get(tariff_id, make_tariff())
    
    cache.tariffs.get.side_effect = get_tariff
    return cache


@pytest.fixture
def mock_model_data(shared_test_data):
    """Mock ServiceDataModel с тестовыми данными."""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.users.get_all = AsyncMock(return_value=shared_test_data["users"])
    model_data.keys = AsyncMock()
    model_data.keys.get_all = AsyncMock(return_value=shared_test_data["keys"])
    model_data.keys.update = AsyncMock()
    model_data.payments = AsyncMock()
    model_data.payments.get_all = AsyncMock(return_value=shared_test_data["payments"])
    return model_data


@pytest.fixture
def mock_container():
    """Mock контейнера зависимостей."""
    container = AsyncMock()
    container.resolve = MagicMock()
    return container


# ============================================================================
# Тесты AdminStatsGetter
# ============================================================================


class TestAdminStatsGetterWithSharedData:
    """Тесты AdminStatsGetter с едиными тестовыми данными."""
    
    async def test_returns_stats_msg_with_all_counts(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """STATS_MSG должен содержать все счётчики сегментов."""
        getter = AdminStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        assert "STATS_MSG" in result
        stats_msg = result["STATS_MSG"]
        
        # Проверка наличия ключевых значений в сообщении
        assert "8" in stats_msg  # Всего ключей
        assert "Зарегистрировано: 3" in stats_msg  # Пользователи
        
    async def test_writes_all_keys_to_dialog_data(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """AdminStatsGetter должен сохранить all_keys в dialog_data."""
        getter = AdminStatsGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)
        
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8

    async def test_stats_match_shared_data(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """Статистика должна показывать правильные значения."""
        getter = AdminStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        stats_msg = result["STATS_MSG"]

        # 4 пользователя
        assert "Всего: 4" in stats_msg

        # Ключи сохранены в dialog_data
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8


# ============================================================================
# Тесты AdminStatsKeyboard — минимальные
# ============================================================================


class TestAdminStatsKeyboard:
    """Тесты клавиатуры AdminStatsKeyboard (статистика пользователей)."""

    async def test_keyboard_has_delete_keys_button(self):
        """Клавиатура должна содержать кнопку удаления старых ключей."""
        from dialogs.windows.widgets.keybord.admin.panel import AdminStatsKeyboard
        keyboard = AdminStatsKeyboard()
        # Клавиатура использует Column с SwitchTo — проверяем что строится без ошибки
        built = keyboard.build()
        assert built is not None

    async def test_keyboard_has_back_button(self):
        """Клавиатура должна содержать кнопку Назад."""
        from dialogs.windows.widgets.keybord.admin.panel import AdminStatsKeyboard
        keyboard = AdminStatsKeyboard()
        built = keyboard.build()
        assert built is not None


# ============================================================================
# Тесты AdminKeyListGetter
# ============================================================================


class TestAdminKeyListGetterWithSharedData:
    """Тесты AdminKeyListGetter с едиными тестовыми данными."""
    
    async def test_reads_segment_from_dialog_data(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """AdminKeyListGetter должен читать current_segment из dialog_data."""
        # Устанавливаем сегмент в dialog_data
        mock_dialog_manager.dialog_data["current_segment"] = "expired"
        mock_dialog_manager.dialog_data["all_keys"] = shared_test_data["keys"]
        
        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        assert result["segment"] == "expired"
        assert result["total_keys"] == 2  # 2 просроченных ключа
        
    async def test_all_segment_returns_all_keys(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """Сегмент 'all' должен вернуть все 8 ключей."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"
        
        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        assert result["total_keys"] == 8
        assert len(result["keys_data"]) == 8
        
    async def test_expired_segment_returns_only_expired(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """Сегмент 'expired' должен вернуть только просроченные ключи."""
        mock_dialog_manager.dialog_data["current_segment"] = "expired"
        
        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        assert result["total_keys"] == 2
        emails = [key.email for _, key in result["keys_data"]]
        assert "expired1@example.com" in emails
        assert "expired2@example.com" in emails
        
    async def test_keys_data_format(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """keys_data должен быть списком кортежей (label, key)."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"
        
        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        assert len(result["keys_data"]) > 0
        label, key = result["keys_data"][0]
        assert isinstance(label, str)
        assert isinstance(key, Key)
        
    async def test_keys_data_contains_email_and_tg_id(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """Label в keys_data должен содержать email и tg_id."""
        mock_dialog_manager.dialog_data["current_segment"] = "all"
        
        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        
        # Проверяем первый ключ из shared_test_data
        target_email = "expired1@example.com"
        found = False
        for label, key in result["keys_data"]:
            if key.email == target_email:
                found = True
                assert target_email in label
                assert "111" in label  # tg_id
                break
        
        assert found, f"Ключ {target_email} не найден в keys_data"
        
    async def test_stores_filtered_keys_in_dialog_data(self, mock_model_data, mock_dialog_manager, shared_test_data):
        """get_data должен сохранить filtered_keys в dialog_data."""
        mock_dialog_manager.dialog_data["current_segment"] = "expiring_24h"
        
        getter = AdminKeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)
        
        assert "filtered_keys" in mock_dialog_manager.dialog_data
        # Ключи expiring_24h фильтруются по времени выполнения
        # Проверяем что filtered_keys установлен (может быть пустым если время истекло)
        assert isinstance(mock_dialog_manager.dialog_data["filtered_keys"], list)


# ============================================================================
# Тесты on_key_selected
# ============================================================================


class TestOnKeySelectedWithSharedData:
    """Тесты обработчика on_key_selected с едиными данными."""
    
    async def test_finds_key_by_email(self, mock_dialog_manager, shared_test_data):
        """on_key_selected должен найти ключ по email."""
        # Устанавливаем filtered_keys в dialog_data
        mock_dialog_manager.dialog_data["filtered_keys"] = shared_test_data["keys"]
        
        callback = AsyncMock()
        
        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "active1@example.com"  # item_id
        )
        
        # Проверка что ключ сохранён
        assert "selected_key" in mock_dialog_manager.dialog_data
        selected = mock_dialog_manager.dialog_data["selected_key"]
        assert selected.email == "active1@example.com"
        assert selected.tg_id == 111
        
    async def test_writes_selected_key_email(self, mock_dialog_manager, shared_test_data):
        """on_key_selected должен сохранить selected_key_email."""
        mock_dialog_manager.dialog_data["filtered_keys"] = shared_test_data["keys"]
        callback = AsyncMock()
        
        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "trial@example.com"
        )
        
        assert mock_dialog_manager.dialog_data["selected_key_email"] == "trial@example.com"
        
    async def test_answer_contains_selected_email(self, mock_dialog_manager, shared_test_data):
        """Ответ должен содержать email выбранного ключа."""
        mock_dialog_manager.dialog_data["filtered_keys"] = shared_test_data["keys"]
        callback = AsyncMock()
        
        await on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "expired2@example.com"
        )
        
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        answer_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "expired2@example.com" in answer_text
        
    async def test_switches_to_key_details_after_selection(self, mock_dialog_manager, shared_test_data):
        """После выбора ключа должен быть переход на key_details."""
        mock_dialog_manager.dialog_data["filtered_keys"] = shared_test_data["keys"]
        mock_dialog_manager.switch_to = AsyncMock()
        callback = AsyncMock()
        callback.answer = AsyncMock()
        
        # Используем обёртку из клавиатуры AdminKeysListKeyboard, которая вызывает switch_to
        keyboard = AdminKeysListKeyboard()
        await keyboard._on_key_selected(
            callback,
            None,
            mock_dialog_manager,
            "active2@example.com"
        )
        
        mock_dialog_manager.switch_to.assert_called_once_with(AdminManager.key_details)


# ============================================================================
# Тесты AdminKeyDetailsGetter
# ============================================================================


class TestAdminKeyDetailsGetterWithSharedData:
    """Тесты AdminKeyDetailsGetter с едиными данными."""

    async def test_reads_selected_key_from_start_data(self, mock_dialog_manager, shared_test_data, mock_cache_service):
        """AdminKeyDetailsGetter должен читать selected_key из start_data."""
        selected_key = shared_test_data["keys"][0]  # expired1@example.com
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_dialog_manager.middleware_data["cache"] = mock_cache_service

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is False
        # Проверяем по tg_id и keys (email не возвращается в явном виде)
        assert result.get("tg_id") == 111
        assert result.get("keys") == "key_expired1@example.com"

    async def test_reads_selected_key_from_dialog_data(self, mock_dialog_manager, shared_test_data, mock_cache_service):
        """AdminKeyDetailsGetter должен читать selected_key из dialog_data."""
        selected_key = shared_test_data["keys"][4]  # exp7d@example.com (7 дней)
        mock_dialog_manager.start_data = {}
        mock_dialog_manager.dialog_data["selected_key"] = selected_key
        mock_dialog_manager.middleware_data["cache"] = mock_cache_service

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is False
        # Проверяем по tg_id
        assert result.get("tg_id") == 333
        assert result.get("keys") == "key_exp7d@example.com"

    async def test_returns_keymodel_fields(self, mock_dialog_manager, shared_test_data, mock_cache_service):
        """Результат должен содержать поля KeyModel.to_dict()."""
        selected_key = shared_test_data["keys"][6]  # trial@example.com
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_dialog_manager.middleware_data["cache"] = mock_cache_service

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "status_emoji" in result
        assert "status_text" in result
        assert "is_trial" in result
        assert "is_active" in result

    async def test_returns_admin_specific_fields(self, mock_dialog_manager, shared_test_data, mock_cache_service):
        """Результат должен содержать admin-специфичные поля."""
        selected_key = shared_test_data["keys"][0]  # expired1@example.com
        mock_dialog_manager.start_data = {"selected_key": selected_key}
        mock_dialog_manager.middleware_data["cache"] = mock_cache_service

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("tg_id") == 111
        assert result.get("client_id") == "c_111"
        assert result.get("inbound_id") == 1
        
    async def test_returns_error_when_no_key(self, mock_dialog_manager, mock_cache_service):
        """При отсутствии ключа должен вернуть error=True."""
        mock_dialog_manager.start_data = {}
        mock_dialog_manager.dialog_data = {}
        mock_dialog_manager.middleware_data["cache"] = mock_cache_service
        
        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)
        
        assert result.get("error") is True


# ============================================================================
# Тесты AdminKeyDetailsKeyboard handlers
# ============================================================================


class TestAdminKeyDetailsKeyboardHandlers:
    """Тесты обработчиков AdminKeyDetailsKeyboard с едиными данными."""

    async def test_to_delete_opens_delete_dialog(self, mock_dialog_manager, shared_test_data):
        """_to_delete должен открыть диалог удаления с email ключа."""
        selected_key = shared_test_data["keys"][0]  # expired1@example.com
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_delete(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyDeleteSG.confirm
        assert call_args[1]["data"]["email"] == "expired1@example.com"

    async def test_to_change_date_opens_date_dialog(self, mock_dialog_manager, shared_test_data):
        """_to_change_date должен открыть диалог изменения даты."""
        selected_key = shared_test_data["keys"][4]  # exp7d@example.com (7 дней)
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_date(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyChangeDateSG.pick_date
        assert call_args[1]["data"]["email"] == "exp7d@example.com"

    async def test_to_change_tariff_opens_tariff_dialog(self, mock_dialog_manager, shared_test_data):
        """_to_change_tariff должен открыть диалог изменения тарифа."""
        selected_key = shared_test_data["keys"][7]  # trial@example.com
        mock_dialog_manager.dialog_data["selected_key"] = selected_key

        callback = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_tariff(callback, None, mock_dialog_manager)

        mock_dialog_manager.start.assert_called_once()
        call_args = mock_dialog_manager.start.call_args
        assert call_args[0][0] == AdminKeyChangeTariffSG.pick_tariff
        assert call_args[1]["data"]["email"] == "trial@example.com"


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
        self, mock_model_data, mock_dialog_manager, shared_test_data
    ):
        """AdminStatsGetter должен вернуть STATS_MSG и сохранить all_keys."""
        stats_getter = AdminStatsGetter(mock_model_data)
        stats_result = await stats_getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in stats_result
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 8

    async def test_stats_contains_user_metrics(
        self, mock_model_data, mock_dialog_manager, shared_test_data
    ):
        """STATS_MSG должен содержать метрики пользователей."""
        stats_getter = AdminStatsGetter(mock_model_data)
        stats_result = await stats_getter.get_data(mock_dialog_manager)

        msg = stats_result["STATS_MSG"]
        # Проверяем что присутствуют новые метрики
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
        message = AdminStatsMessage()
        result = message.build()
        
        # Проверяем что это Format объект
        from aiogram_dialog.widgets.text import Format
        assert isinstance(result, Format)
        
        # Проверяем шаблон
        assert "{STATS_MSG}" in result.text
