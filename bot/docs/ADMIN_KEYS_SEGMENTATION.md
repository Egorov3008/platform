# Сегментация ключей в админ-панели

## Обзор

Админ-панель теперь использует сегментацию ключей для удобного фильтрования и администрирования ключей пользователей. Поддерживается:

- 📋 **Все ключи** — полный список всех ключей
- ⏰ **Ключи на 24h** — ключи, истекающие в ближайшие 24 часа
- 🔴 **Просроченные ключи** — уже истёкшие ключи

Каждый список поддерживает **пагинацию** и **выбор ключа** для администрирования.

## Архитектура

### Компоненты

```
AdminStatsKeyboard (кнопки)
    ↓
AdminKeysHandler (обработчики)
    ↓
KeySegmentationService (сегментация)
    ↓
AdminKeyListGetter (геттер списка)
    ↓
AdminKeyDetailsGetter (геттер деталей)
```

### Файлы

```
dialogs/windows/widgets/keybord/admin/
└── panel.py                 # Обновлённые кнопки AdminStatsKeyboard

getters/on_click/
└── admin_keys.py           # Новые обработчики с сегментацией

dialogs/windows/getters/admin/
├── panel.py                # Обновлённый AdminStatsGetter
└── keys_list.py            # Новые геттеры для списков
```

## Использование

### 1️⃣ Обновлённые кнопки в AdminStatsKeyboard

```python
Button(Const("📋 Все ключи"), id="all_keys", on_click=self._on_all_keys),
Button(Const("⏰ Ключи на 24h"), id="24h_keys", on_click=self._on_24h_keys),
Button(Const("🔴 Просроченные ключи"), id="expired_keys", on_click=self._on_expired_keys),
```

Каждая кнопка:
- Получает все ключи из кеша
- Фильтрует по сегменту с использованием `KeySegmentationService`
- Сохраняет результаты в `dialog_data`
- Отображает количество найденных ключей

### 2️⃣ Обработчики (AdminKeysHandler)

```python
# Показать ключи на 24h
async def on_click_24h_keys(callback, button, manager):
    all_keys = await cache.keys.all()
    expiring_24h = await segmentation.get_expiring_24h(all_keys)

    manager.dialog_data["current_segment"] = "expiring_24h"
    manager.dialog_data["filtered_keys"] = expiring_24h
```

**Сохраняемые данные:**
- `current_segment` — название текущего сегмента
- `filtered_keys` — список отфильтрованных ключей
- `total_filtered` — количество ключей в текущем сегменте

### 3️⃣ Геттеры для отображения

#### AdminKeyListGetter — список ключей с пагинацией

```python
# Используется в Select виджете для пагинации
keys_data = [
    (f"{key.email} ({key.tg_id})", key)
    for key in filtered_keys
]

# Отображает:
# - Название сегмента
# - Количество найденных ключей
# - Список ключей для выбора
```

#### AdminKeyDetailsGetter — детали выбранного ключа

```python
# Отображает:
# 📧 Email: user@example.com
# 👤 Пользователь: 123456789
# 🔑 Client ID: abc123
# Статус: ✅ Активный
# Трафик: 📊 45.23 Гб
# Inbound: 1
# Тариф: 5
# ⏱️ Создан: 1234567890
# 📅 Истекает: 1234567890
```

## Примеры

### Пример 1: Обновить AdminStatsGetter в DI контейнере

```python
from dialogs.windows.getters.admin.panel import AdminStatsGetter

# Регистрируем в контейнере
container.register(
    AdminStatsGetter,
    factory=lambda service_model: AdminStatsGetter(service_model),
)
```

### Пример 2: Добавить окно со списком ключей

```python
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Select, Column, Button, Cancel
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.getters.admin.keys_list import AdminKeyListGetter
from states import AdminManager

# Определяем окно со списком ключей
keys_list_window = Window(
    Format("{keys_message}"),
    Column(
        Select(
            Format("{item[0]}"),
            id="keys_select",
            item_id_getter=lambda x: x[0].email,
            items="keys_data",
            on_click=on_key_selected,
        ),
    ),
    Cancel(Const("🔙 Назад")),
    state=AdminManager.key_list,
    getter=AdminKeyListGetter(model_data),
)
```

### Пример 3: Администрирование выбранного ключа

```python
from dialogs.windows.getters.admin.keys_list import AdminKeyDetailsGetter

# Окно с деталями ключа
key_details_window = Window(
    Format("{key_details}"),
    Column(
        Button(
            Const("❌ Удалить ключ"),
            id="delete_key",
            on_click=delete_key_handler,
        ),
        Button(
            Const("⏳ Продлить ключ"),
            id="renew_key",
            on_click=renew_key_handler,
        ),
        Button(
            Const("🔄 Изменить тариф"),
            id="change_tariff",
            on_click=change_tariff_handler,
        ),
        Cancel(Const("🔙 Назад")),
    ),
    state=AdminManager.key_details,
    getter=AdminKeyDetailsGetter(),
)
```

## Поток данных

```
Нажимаем кнопку "Ключи на 24h"
    ↓
on_click_24h_keys()
    ↓
Получить все ключи из CacheService
    ↓
Фильтровать через KeySegmentationService
    ↓
Сохранить в dialog_data["filtered_keys"]
    ↓
Отобразить список в Select (с пагинацией)
    ↓
Пользователь выбирает ключ
    ↓
on_key_selected()
    ↓
Сохранить в dialog_data["selected_key"]
    ↓
Отобразить детали в AdminKeyDetailsGetter
    ↓
Админ может удалить/продлить/изменить тариф
```

## Обработчики администрирования

Для каждого действия над ключом нужно создать обработчик:

```python
async def delete_key_handler(callback, button, manager):
    """Удалить выбранный ключ."""
    selected_key = manager.dialog_data.get("selected_key")
    cache = manager.middleware_data.get("cache")

    # Удаление...
    await cache.keys.delete(selected_key.email)

    await callback.answer("✅ Ключ удален")

async def renew_key_handler(callback, button, manager):
    """Продлить ключ на 30 дней."""
    selected_key = manager.dialog_data.get("selected_key")

    # Продление...
    new_expiry = selected_key.expiry_time + (30 * 24 * 3600 * 1000)
    selected_key.expiry_time = new_expiry

    await callback.answer("✅ Ключ продлён на 30 дней")

async def change_tariff_handler(callback, button, manager):
    """Изменить тариф ключа."""
    selected_key = manager.dialog_data.get("selected_key")
    new_tariff_id = manager.dialog_data.get("new_tariff_id")

    # Изменение тарифа...
    selected_key.tariff_id = new_tariff_id

    await callback.answer("✅ Тариф изменён")
```

## Сегменты в админ-панели

| Кнопка | Сегмент | Фильтр |
|--------|---------|--------|
| 📋 Все ключи | `all` | Все ключи без фильтра |
| ⏰ Ключи на 24h | `expiring_24h` | Истекают в 24 часа |
| 🔴 Просроченные | `expired` | Уже истекшие |

## Производительность

- **Время фильтрации:** O(n) где n — количество ключей
- **Кеширование:** 5 минут на результат
- **Пагинация:** Select виджет автоматически поддерживает пагинацию при > 10 элементов

## Интеграция с существующими окнами

Новая функциональность полностью совместима с существующей структурой диалогов:

- ✅ Использует `CacheService` согласно правилам
- ✅ Работает с `ServiceDataModel` для получения данных
- ✅ Поддерживает `dialog_data` для передачи между окнами
- ✅ Использует новые обработчики из `admin_keys.py`

## Тестирование

```bash
# Протестировать сегментацию
pytest tests/services/core/segmentation/test_key_segmenter.py -v

# Протестировать админ-геттеры
pytest tests/dialogs/getters/admin/ -v
```
