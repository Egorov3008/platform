# Администраторские диалоги (Admin Dialogs)

Документация для модуля admin-диалогов, реализованных с использованием новой архитектуры `WindowFactory + CacheService`.

## Обзор

Администраторские диалоги обеспечивают функционал для управления VPN-подписками, пользователями и рассылками:

- **Панель администратора** — статистика, управление ключами, синхронизация
- **Поиск** — поиск пользователей по ID и ключей по email
- **Рассылка** — отправка сообщений всем пользователям

## Архитектура

### Компонентная структура

Все admin-диалоги построены с использованием **3-уровневого паттерна**:

```
MessageBuilder + KeyboardBuilder + DataGetter
         ↓
     WindowFactory
         ↓
      Window (aiogram-dialog)
```

**Файлы по уровням:**

| Уровень | Директория | Файлы |
|---------|-----------|-------|
| Messages | `dialogs/windows/widgets/message/admin/` | panel.py, search.py, mailing.py |
| Keyboards | `dialogs/windows/widgets/keybord/admin/` | panel.py, search.py, mailing.py |
| Getters | `dialogs/windows/getters/admin/` | panel.py, mailing.py |
| DI | `services/conteiner/registrate/getters/` | admin.py |

### Поток данных

```
User Input (Telegram)
    ↓
Keyboard Handler (on_click)
    ↓
DialogManager (state management)
    ↓
DataGetter (fetch data from CacheService)
    ↓
MessageBuilder + KeyboardBuilder (render UI)
    ↓
Window Display (aiogram-dialog)
```

## Диалоги и состояния

### 1. Панель администратора (AdminManager)

**3 окна:**

#### AdminManager.main
**Сообщение:** `🤖 Панель администратора`

**Кнопки:**
- 📊 Статистика пользователей → `AdminManager.static_user`
- 👥 Поиск → `AdminSearchManagementSG.main`
- 📢 Массовая рассылка → `AdminMassMailing.receiving_message`
- 🔄 Синхронизация панели и БД → `click_sync_cache()`
- 🔙 Назад → `MainMenu.main`

**Класс:** `AdminMainKeyboard`

#### AdminManager.static_user
**Сообщение:** Форматированная статистика пользователей и ключей (из `AdminStatsGetter`)

```python
<b>📊 Статистика</b>

👥 <b>Пользователей:</b> {total_users}
🔑 <b>Ключей:</b> {total_keys}
🆕 За неделю: {week_registrations}
📈 За месяц: {month_registrations}
📉 Отток: {churn_rate}%
🚫 Заблокировано: {blocked_users}
```

**Кнопки:**
- 📋 Все ключи → `on_click_all_keys()` → `AdminKeyManagementSG.key_list`
- 📥 Выгрузить оплаты в CSV → `on_click_export_csv_handler()`
- 📊 Статистика ключей → `AdminManager.key_stats`
- 💰 Статистика платежей → `AdminManager.payment_stats`
- 🔙 Назад → `AdminManager.main`

**Getter:** `AdminStatsGetter` — собирает метрики пользователей из CacheService (регистрации, отток, заблокированные)

```python
class AdminStatsGetter(DataGetter):
    def __init__(self, model_data: ServiceDataModel):
        self.users = model_data.users
        self.keys = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        # Вычисляет total_users и total_keys из кеша
        # Сохраняет ключи в dialog_data для обработчиков
```

#### AdminManager.confirmation_deletion_keys
**Сообщение:** `Для удаления подходит {old_keys} ключей`

**Кнопки:**
- Удалить → `delete_expired_keys_fast()` (удаляет просроченные ключи)
- 🔙 Назад → `AdminManager.static_user`

**Getter:** `AdminConfirmDeleteGetter` — считает просроченные ключи

#### AdminManager.key_stats
**Сообщение:** Детальная статистика ключей с разбивкой по тарифам (из `KeyStatsGetter`)

```
🔑 Статистика ключей:

📊 Все ключи:
   Всего: 156
   🧪 Trial:
     • Trial (30 мин): 45
     • Trial (1 час): 12
   💰 Платные:
     • Месячный: 67
     • Годовой: 23
   💤 Неиспользуемые: 9

⏰ Истекают 24h:
   Всего: 23
   🧪 Trial: 15
   💰 Платные: 6
   💤 Неиспользуемые: 2

📢 Уведомления 24h:
   ✅ 10h отправлено: 18 / ❌ Не отправлено: 5
   ✅ 24h отправлено: 20 / ❌ Не отправлено: 3
```

**Кнопки:**
- 🔙 Назад → `AdminManager.static_user`

**Getter:** `KeyStatsGetter` — анализирует все ключи, группирует по тарифам, выявляет истекающие в течение 24h

#### AdminManager.payment_stats
**Сообщение:** Статистика платежей и прогноз выручки (из `PaymentStatsGetter`)

```
💰 Статистика платежей

📊 Выручка:
   📅 За год: 1,234,567.89 ₽ (456 плат.)
   🗓️ За месяц: 123,456.78 ₽ (45 плат.)
   📆 За неделю: 34,567.89 ₽ (12 плат.)
   ☀️ За сегодня: 5,678.90 ₽ (2 плат.)

   💳 Средний чек (мес): 2,743.48 ₽

🔮 Прогноз выручки:
   🟢 Следующая неделя: 38,900.00 ₽ (75%)
      Метод: комбинированный
   🟡 Следующий месяц: 145,000.00 ₽ (55%)
      Метод: скользящее среднее

📈 Тренд: +12.5%
```

**Кнопки:**
- 🔙 Назад → `AdminManager.static_user`

**Getter:** `PaymentStatsGetter` — использует `PaymentMetricsService` для расчёта выручки и прогнозов

---

### 2. Поиск (AdminSearchManagementSG)

**3 окна:**

#### AdminSearchManagementSG.main
**Сообщение:** `Выберете метод поиска 📌`

**Кнопки:**
- SwitchTo: Поиск пользователя по id 🆔 → `AdminSearchManagementSG.search_tg_id`
- SwitchTo: Поиск ключа по email 📨 → `AdminSearchManagementSG.search_email`
- Back: Назад

**Класс:** `SearchMainKeyboard`

#### AdminSearchManagementSG.search_tg_id
**Сообщение:** `Введите tg_id:`

**TextInput:**
- ID: `tg_id`
- Type: `int`
- On Success: `on_click_search_tg_id()` → запускает `AdminUserManagement.profile_user`
- On Error: `error_tg_id()` → "ID Должен быть числом!"

**Кнопка:** Back: Назад

**Класс:** `SearchTgIdKeyboard`

```python
# Обработчик
async def on_click_search_tg_id(message, widget, manager, text: str):
    tg_id = int(text)
    await manager.start(AdminUserManagement.profile_user, data={"tg_id": tg_id})
```

#### AdminSearchManagementSG.search_email
**Сообщение:** `Введите email`

**TextInput:**
- ID: `email`
- Type: `str`
- On Success: `on_click_search_email()` → запускает `AdminKeyManagementSG.process_key_edit`
- On Error: `error_email()` → "EMAIL должен быть строкой!"

**Кнопка:** Back: Назад

**Класс:** `SearchEmailKeyboard`

```python
# Обработчик
async def on_click_search_email(message, widget, manager, text: str):
    email = str(text)
    await manager.start(AdminKeyManagementSG.process_key_edit, data={"email": email})
```

---

### 3. Массовая рассылка (AdminMassMailing)

**2 окна:**

#### AdminMassMailing.receiving_message
**Сообщение:** `✉️ Введите сообщение для рассылки:`

**TextInput:**
- ID: `text`
- Type: `str`
- On Success: `on_click_confirmation_of_sending()` → switch to confirmation
- Сохраняет в `dialog_data["text"]`

**Кнопки:**
- Button: ◀️ Отмена → `manager.done()`

**Класс:** `MailingInputKeyboard`

#### AdminMassMailing.confirmation
**Сообщение:** `📬 Вы уверены, что хотите отправить сообщение:\n\n<i>{text}</i>?`

**Radio (для выбора режима закрепления):**
- Items: `[("📍 Закрепить сообщение", 1), ("❌ Не закреплять", 2)]`
- ID: `pin_message`
- On Click: `on_click_change_status()` → сохраняет в `dialog_data["pin_message"]`

**Кнопки:**
- Button: 🔄 Изменить сообщение → switch to `AdminMassMailing.receiving_message`
- Button: ✅ Подтвердить отправку → `on_click_mass_mailing()` (отправляет всем пользователям)
- Button: ◀️ Отмена → `manager.done()`

**Getter:** `MailingConfirmGetter` — читает текст из dialog_data и возвращает список статусов

```python
class MailingConfirmGetter(DataGetter):
    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        text = dialog_manager.dialog_data.get("text", "Не задано")
        statuses = [
            ("📍 Закрепить сообщение", 1),
            ("❌ Не закреплять", 2),
        ]
        return {"text": text, "statuses": statuses}
```

**Класс:** `MailingConfirmKeyboard`

---

## Обработчики (on_click handlers)

### Обновленные функции с CacheService

#### on_click_all_keys
```python
async def on_click_all_keys(callback, button, dialog_manager):
    """Показывает все ключи"""
    cache_service = dialog_manager.middleware_data.get("cache")
    keys = await cache_service.keys.all()
    await dialog_manager.start(AdminKeyManagementSG.key_list, data={"all_keys": keys})
```

#### on_click_24h_keys
```python
async def on_click_24h_keys(callback, button, dialog_manager):
    """Показывает ключи, истекающие в течение 24 часов"""
    keys_24h = dialog_manager.dialog_data.get("users_expiring_24_hours", [])
    await dialog_manager.start(AdminKeyManagementSG.key_list, data={"all_keys": keys_24h})
```

#### on_click_expired_keys
```python
async def on_click_expired_keys(callback, button, dialog_manager):
    """Показывает просроченные ключи"""
    cache_service = dialog_manager.middleware_data.get("cache")
    keys = await cache_service.keys.all()
    # Фильтруем просроченные
    expired = [k for k in keys if k.expiry_time < current_timestamp]
    await dialog_manager.start(AdminKeyManagementSG.key_list, data={"all_keys": expired})
```

#### on_click_mass_mailing
```python
async def on_click_mass_mailing(callback, widget, dialog_manager):
    """Отправляет сообщение всем пользователям"""
    cache_service = dialog_manager.middleware_data.get("cache")
    users = await cache_service.users.all()
    pin_mode = dialog_manager.dialog_data.get("pin_message")
    text = dialog_manager.dialog_data.get("text")

    # Отправляет сообщение с семафором на 50 одновременных запросов
    # Результат: количество успешных/неудачных отправок
```

#### delete_expired_keys_fast
```python
async def delete_expired_keys_fast(callback, button, manager):
    """Удаляет все просроченные ключи из БД и кеша"""
    cache = manager.middleware_data.get("cache")
    session = manager.middleware_data.get("session")

    # 1. Получает все ключи из кеша
    # 2. Фильтрует просроченные
    # 3. Удаляет из БД: DELETE FROM keys WHERE email = $1
    # 4. Удаляет из кеша: cache.keys.delete(email)
    # 5. Возвращает количество удаленных
```

---

## Getters (DataGetter)

### AdminStatsGetter

**Цель:** Собрать метрики пользователей и ключей

**Входные данные:** ServiceDataModel (DI)

**Выходные данные:**
```python
{
    "STATS_MSG": "<b>📊 Статистика</b>\n\n👥 <b>Пользователей:</b> 42\n🔑 <b>Ключей:</b> 156\n🆕 За неделю: 5\n📈 За месяц: 18\n📉 Отток: 3.2%\n🚫 Заблокировано: 2",
    "total_users": 42,
    "total_keys": 156,
    "week_registrations": 5,
    "month_registrations": 18,
    "churn_rate": 3.2,
    "blocked_users": 2,
}
```

**Реализация:**
```python
class AdminStatsGetter(DataGetter):
    def __init__(self, model_data: ServiceDataModel):
        self.users = model_data.users
        self.keys = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        all_users = await self.users.get_all()
        all_keys = await self.keys.get_all()

        total_users = len(all_users) if isinstance(all_users, list) else 1 if all_users else 0
        total_keys = len(all_keys) if isinstance(all_keys, list) else 1 if all_keys else 0

        # Рассчитываем регистрации за неделю/месяц
        # Вычисляем отток (churn rate)
        # Считаем заблокированных пользователей

        return {
            "STATS_MSG": stats_msg,
            "total_users": total_users,
            "total_keys": total_keys,
            # ... другие метрики
        }
```

### KeyStatsGetter

**Цель:** Собрать детальную статистику ключей с разбивкой по тарифам и 24h окну

**Входные данные:** ServiceDataModel (DI)

**Выходные данные:**
```python
{
    "STATS_MSG": "🔑 Статистика ключей:\n\n...",
    "stats": {
        "all_total": 156,
        "all_trial": 57,
        "all_paid": 90,
        "all_unused": 9,
        "all_trial_by_tariff": {"Trial (30 мин)": 45, "Trial (1 час)": 12},
        "all_paid_by_tariff": {"Месячный": 67, "Годовой": 23},
        "expiring_24h_total": 23,
        "expiring_24h_trial": 15,
        "expiring_24h_paid": 6,
        "expiring_24h_unused": 2,
        "notified_10h_true": 18,
        "notified_10h_false": 5,
        "notified_24h_true": 20,
        "notified_24h_false": 3,
    },
    "all_keys": [...],
    "expiring_24h_keys": [...],
}
```

**Методы:**
- `_resolve_tariff_name(tariff_id)` — получает название тарифа по ID
- `_group_by_tariff_names(keys)` — группирует ключи по названиям тарифов
- `_categorize_keys(keys)` — разбивает на trial/paid/unused
- `_format_tariff_breakdown(by_tariff)` — форматирует разбивку в строку

### PaymentStatsGetter

**Цель:** Собрать статистику платежей и сформировать прогноз выручки

**Входные данные:** PaymentMetricsService (DI)

**Выходные данные:**
```python
{
    "PAYMENT_STATS_MSG": "💰 <b>Статистика платежей</b>\n\n...",
    "revenue_stats": {
        "year_total": 1234567.89,
        "month_total": 123456.78,
        "week_total": 34567.89,
        "day_total": 5678.90,
        "year_payments": 456,
        "month_payments": 45,
        "week_payments": 12,
        "day_payments": 2,
    },
    "forecast": {
        "week_forecast": 38900.00,
        "week_confidence": 75,
        "month_forecast": 145000.00,
        "month_confidence": 55,
        "growth_trend": 12.5,
    },
    "last_updated": "04.04.2026 23:00",
}
```

**Особенности:**
- Использует `PaymentMetricsService.get_revenue_stats()` для расчёта выручки
- Использует `PaymentMetricsService.forecast_revenue()` для прогнозов
- Прогнозы основаны на комбинированном методе (60% moving_avg + 40% linear_regression)
- Показывает уверенность прогноза (🟢 >70%, 🟡 >40%, 🔴 <40%)

### AdminConfirmDeleteGetter

**Цель:** Подсчитать количество просроченных ключей

**Входные данные:** ServiceDataModel (DI)

**Выходные данные:**
```python
{
    "old_keys": 12  # Количество просроченных ключей
}
```

### MailingConfirmGetter

**Цель:** Подготовить данные для подтверждения рассылки

**Входные данные:** dialog_manager.dialog_data (уже заполнено TextInput)

**Выходные данные:**
```python
{
    "text": "Текст сообщения от пользователя",
    "statuses": [("📍 Закрепить сообщение", 1), ("❌ Не закреплять", 2)]
}
```

---

## DI контейнер (Dependency Injection)

### AdminRegistrar

**Файл:** `services/conteiner/registrate/getters/admin.py`

**Регистрирует:**
- ✅ **Getters**: AdminStatsGetter, KeyStatsGetter, PaymentStatsGetter, MailingConfirmGetter
- ✅ **Messages**: 10+ классов (AdminMainMessage, KeyStatsMessage, PaymentStatsMessage и т.д.)
- ✅ **Keyboards**: 10+ классов (AdminMainKeyboard, KeyStatsKeyboard, PaymentStatsKeyboard и т.д.)

**Пример регистрации:**
```python
class AdminRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        # Getters с зависимостями
        def build_admin_stats_getter():
            return AdminStatsGetter(
                model_data=container.resolve(ServiceDataModel)
            )

        container.register(
            AdminStatsGetter,
            factory=build_admin_stats_getter,
            scope=punq.Scope.singleton
        )

        # Message builders без зависимостей
        container.register(
            AdminMainMessage,
            factory=lambda: AdminMainMessage(),
            scope=punq.Scope.singleton
        )
```

**Использование:**
```python
# В window_factory.py
def _create_dependence(self, cls_name: str) -> Any:
    return self.container.resolve(cls_name)  # AdminRegistrar уже зарегистрирован
```

---

## CacheService использование

### ✅ Правильные паттерны

```python
# 1. Получить из middleware_data
cache_service: Optional[CacheService] = manager.middleware_data.get("cache")

# 2. Получить все объекты
users = await cache_service.users.all()
keys = await cache_service.keys.all()

# 3. Получить конкретный объект
user = await cache_service.users.get(tg_id)
key = await cache_service.keys.get(email)  # ⚠️ Key использует email, не id!

# 4. Установить значение
await cache_service.users.set(tg_id, user_obj)
await cache_service.keys.set(email, key_obj)

# 5. Удалить значение
await cache_service.users.delete(tg_id)
await cache_service.keys.delete(email)
```

### ❌ Неправильные паттерны (ЗАПРЕЩЕНЫ)

```python
# ❌ Прямой доступ к ModelCache
await cache.get_all_keys()  # cache_instance из legacy

# ❌ Попытка получить Key по ID (Key использует email!)
await cache_service.keys.get(key.id)
```

---

## Window Config (dialogs/windows/__init__.py)

### Регистрация окон

```python
# Админ диалоги: панель администратора
admin_panel_windows = [
    {
        "state": AdminManager.main,
        "message_cls": AdminMainMessage,
        "keyboard_cls": AdminMainKeyboard,
        "getter_cls": None,
    },
    {
        "state": AdminManager.static_user,
        "message_cls": AdminStatsMessage,
        "keyboard_cls": AdminStatsKeyboard,
        "getter_cls": AdminStatsGetter,
    },
    {
        "state": AdminManager.key_stats,
        "message_cls": KeyStatsMessage,
        "keyboard_cls": KeyStatsKeyboard,
        "getter_cls": KeyStatsGetter,
    },
    {
        "state": AdminManager.payment_stats,
        "message_cls": PaymentStatsMessage,
        "keyboard_cls": PaymentStatsKeyboard,
        "getter_cls": PaymentStatsGetter,
    },
]

# Админ диалоги: поиск
admin_search_windows = [
    {"state": AdminSearchManagementSG.main, "message_cls": SearchMainMessage, ...},
    {"state": AdminSearchManagementSG.search_tg_id, "message_cls": SearchTgIdMessage, ...},
    {"state": AdminSearchManagementSG.search_email, "message_cls": SearchEmailMessage, ...},
]

# Админ диалоги: рассылка
admin_mailing_windows = [
    {"state": AdminMassMailing.receiving_message, "message_cls": MailingInputMessage, ...},
    {"state": AdminMassMailing.confirmation, "message_cls": MailingConfirmMessage, ...},
]

ALL_WINDOW_CONFIGS = (
    # ... существующие окна ...
    + admin_panel_windows
    + admin_search_windows
    + admin_mailing_windows  # Всего 8 новых окон
)
```

---

## Тестирование

### Запуск тестов
```bash
# Все тесты диалогов
pytest tests/dialogs/ -xvs

# Только тесты window factory
pytest tests/dialogs/windows/test_window_factory.py -xvs

# Проверка что все 38 окон загружены
python -c "from dialogs.windows import ALL_WINDOW_CONFIGS; print(len(ALL_WINDOW_CONFIGS))"
# ✓ 38
```

### Проверка окон
```python
# Проверить что все состояния уникальны
assert len({cfg['state'] for cfg in ALL_WINDOW_CONFIGS}) == len(ALL_WINDOW_CONFIGS)

# Проверить что все окна регистрируются
from dialogs import DialogRegistry
registry = DialogRegistry()
# ✓ 8 admin окон должны быть в registry
```

---

## Миграция от старой архитектуры

### Старая архитектура (YAML + DLS)
```yaml
# dialogs/shema/admin/main/adminpanel_flow.yaml
windows:
  - id: admin_main
    text: "🤖 Панель администратора"
    buttons:
      - text: "📊 Статистика"
        action: switch_to
        state: admin.static_user
```

### Новая архитектура (WindowFactory)
```python
# dialogs/windows/widgets/message/admin/panel.py
class AdminMainMessage(MessageBuilder):
    def build(self):
        return Const("🤖 Панель администратора")

# dialogs/windows/widgets/keybord/admin/panel.py
class AdminMainKeyboard(KeyboardBuilder):
    def build(self):
        return Column(
            SwitchTo(Const("📊 Статистика"), id="user_stats", state=AdminManager.static_user),
            ...
        )

# dialogs/windows/__init__.py
admin_panel_windows = [
    {
        "state": AdminManager.main,
        "message_cls": AdminMainMessage,
        "keyboard_cls": AdminMainKeyboard,
        "getter_cls": None,
    },
]
```

### Преимущества новой архитектуры
✅ **Type-safe** — полная поддержка типов Python
✅ **Testable** — каждый компонент легко тестируется отдельно
✅ **DI-friendly** — встроенная поддержка Dependency Injection
✅ **No YAML parsing** — компилируется статически, без runtime парсинга
✅ **Refactoring-safe** — IDE может отрефакторить код автоматически

---

## TODO и известные проблемы

### ⚠️ Требует миграции
- [ ] `on_click_date_selection()` — использует legacy `key_srv`
- [ ] `on_click_restore_trial()` — использует legacy `user_srv`
- [ ] `on_click_view_tariff_admin()` — использует legacy `key_srv`
- [ ] Удалить fallback-импорты `utils_bot.cache_instance` и `services.synchron.working_panel`

### 🔧 Оптимизация
- [ ] Реализовать пагинацию для списков (>100 ключей)
- [ ] Добавить фильтры в KeyStatsGetter (по дате, серверу)
- [ ] Добавить фильтры в PaymentStatsGetter (по тарифу, периоду)
- [ ] Реализовать отмену рассылки в процессе (cancel_token)
- [ ] Добавить экспорт статистики в CSV/Excel

---

## Контакты и примеры

**Входная точка для admin-диалогов:**
```python
# handler: /admin → AdminManager.main
@router.command("admin")
async def admin_panel(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(AdminManager.main)
```

**Полная цепочка для поиска пользователя:**
```
/admin → AdminManager.main (кнопка "Поиск")
→ AdminSearchManagementSG.main (выбрать метод поиска)
→ AdminSearchManagementSG.search_tg_id (TextInput для ID)
→ on_click_search_tg_id() вызывает handler
→ AdminUserManagement.profile_user (результаты поиска)
```

**Полная цепочка для рассылки:**
```
AdminManager.main (кнопка "Рассылка")
→ AdminMassMailing.receiving_message (ввод текста)
→ on_click_confirmation_of_sending() + switch_to()
→ AdminMassMailing.confirmation (выбор режима пиннинга)
→ on_click_mass_mailing() отправляет всем пользователям
```

---

*Документация создана для версии архитектуры WindowFactory + CacheService*
*Последнее обновление: 2026-02-27*
