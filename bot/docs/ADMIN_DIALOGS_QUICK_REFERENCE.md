# Admin Dialogs — Краткий справочник

**Быстрый старт** для разработчиков, работающих с администраторскими диалогами.

## 📍 Где найти коды?

```
dialogs/windows/
├── widgets/
│   ├── message/admin/          ← Сообщения (3 файла)
│   │   ├── panel.py            ← AdminMainMessage, AdminStatsMessage, ...
│   │   ├── search.py           ← SearchMainMessage, SearchTgIdMessage, ...
│   │   └── mailing.py          ← MailingInputMessage, MailingConfirmMessage
│   └── keybord/admin/          ← Клавиатуры (3 файла)
│       ├── panel.py            ← AdminMainKeyboard, AdminStatsKeyboard, ...
│       ├── search.py           ← SearchMainKeyboard, SearchTgIdKeyboard, ...
│       └── mailing.py          ← MailingInputKeyboard, MailingConfirmKeyboard
├── getters/admin/              ← Получение данных (2 файла)
│   ├── panel.py                ← AdminStatsGetter, AdminConfirmDeleteGetter
│   └── mailing.py              ← MailingConfirmGetter
└── __init__.py                 ← Регистрация в ALL_WINDOW_CONFIGS

services/conteiner/registrate/getters/
└── admin.py                    ← AdminRegistrar (DI регистрация)

getters/
├── on_click/admin_click.py     ← Обработчики кнопок
└── workers.py                  ← delete_expired_keys_fast()
```

## 🎯 Основные состояния

| Состояние | Класс | Назначение |
|-----------|-------|-----------|
| AdminManager.main | AdminMainMessage/Keyboard | 🤖 Главная панель администратора |
| AdminManager.static_user | AdminStatsMessage/Keyboard | 📊 Статистика и управление ключами |
| AdminManager.confirmation_deletion_keys | AdminConfirmDeleteMessage/Keyboard | ⚠️ Подтверждение удаления |
| AdminSearchManagementSG.main | SearchMainMessage/Keyboard | 🔍 Выбор метода поиска |
| AdminSearchManagementSG.search_tg_id | SearchTgIdMessage/Keyboard | 🆔 Ввод tg_id |
| AdminSearchManagementSG.search_email | SearchEmailMessage/Keyboard | 📧 Ввод email |
| AdminMassMailing.receiving_message | MailingInputMessage/Keyboard | ✉️ Ввод сообщения |
| AdminMassMailing.confirmation | MailingConfirmMessage/Keyboard | 📬 Подтверждение рассылки |

## 🔧 Как добавить кнопку в админ-панель?

```python
# 1. Отредактировать AdminMainKeyboard в dialogs/windows/widgets/keybord/admin/panel.py

class AdminMainKeyboard(KeyboardBuilder):
    def build(self):
        return Column(
            # Существующие кнопки...

            # Добавить новую кнопку:
            Button(
                Const("🆕 Новая функция"),
                id="new_feature",
                on_click=self._on_new_feature  # Или любой другой обработчик
            ),
        )

    @staticmethod
    async def _on_new_feature(callback, button, manager):
        await callback.answer("Функция работает!", show_alert=True)
        # Или переход в другое состояние:
        # await manager.switch_to(SomeState)
```

## 📨 Как добавить новый getter для данных?

```python
# 1. Создать в dialogs/windows/getters/admin/

from dialogs.windows.base import DataGetter
from services.core.data.service import ServiceDataModel

class MyAdminGetter(DataGetter):
    def __init__(self, model_data: ServiceDataModel):
        self.users = model_data.users
        self.keys = model_data.keys

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        users = await self.users.get_all()
        return {
            "user_count": len(users) if isinstance(users, list) else 1,
            "users": users,
        }

# 2. Зарегистрировать в AdminRegistrar (services/conteiner/registrate/getters/admin.py)

def build_my_admin_getter():
    return MyAdminGetter(model_data=container.resolve(ServiceDataModel))

container.register(MyAdminGetter, factory=build_my_admin_getter, scope=punq.Scope.singleton)

# 3. Использовать в окне (dialogs/windows/__init__.py)

{
    "state": AdminManager.my_state,
    "message_cls": MyMessage,
    "keyboard_cls": MyKeyboard,
    "getter_cls": MyAdminGetter,  ← Указать getter
}
```

## 🔌 Работа с CacheService

```python
# Получить CacheService из middleware
cache_service = dialog_manager.middleware_data.get("cache")

if not cache_service:
    await callback.answer("❌ Ошибка доступа", show_alert=True)
    return

# ✅ Правильно:
users = await cache_service.users.all()          # Получить всех
user = await cache_service.users.get(tg_id)      # Получить одного
await cache_service.users.set(tg_id, user_obj)   # Сохранить
await cache_service.users.delete(tg_id)          # Удалить

keys = await cache_service.keys.all()
key = await cache_service.keys.get(email)        # ⚠️ Key использует email, не id!
await cache_service.keys.set(email, key_obj)

inbounds = await cache_service.inbounds.all()
inbound = await cache_service.inbounds.get((server_id, inbound_id))  # Кортеж!

# ❌ Неправильно:
await cache.get_key(email)         # Legacy API - ЗАПРЕЩЕНО
await cache_service.keys.get(key.id)  # Key.id не существует, используй email!
await cache_service.inbounds.get(inbound_id)  # Неполный ID
```

## 🎬 Основные обработчики (on_click handlers)

### on_click_all_keys
```python
# Показывает все ключи в AdminKeyManagementSG.key_list
# Находится в: getters/on_click/admin_click.py
async def on_click_all_keys(callback, button, dialog_manager):
    cache = dialog_manager.middleware_data.get("cache")
    keys = await cache.keys.all()
    await dialog_manager.start(AdminKeyManagementSG.key_list, data={"all_keys": keys})
```

### on_click_mass_mailing
```python
# Отправляет сообщение всем пользователям
async def on_click_mass_mailing(callback, widget, dialog_manager):
    cache = dialog_manager.middleware_data.get("cache")
    users = await cache.users.all()
    pin_mode = dialog_manager.dialog_data.get("pin_message")
    text = dialog_manager.dialog_data.get("text")
    # Отправляет всем в paralel с семафором на 50
```

### delete_expired_keys_fast
```python
# Удаляет просроченные ключи из БД и кеша
# Находится в: getters/workers.py
async def delete_expired_keys_fast(callback, button, manager):
    cache = manager.middleware_data.get("cache")
    session = manager.middleware_data.get("session")
    # 1. Получает все ключи из кеша
    # 2. Фильтрует просроченные
    # 3. Удаляет из БД и кеша
    # 4. Возвращает количество удаленных
```

## 🧪 Тестирование

```bash
# Все диалоговые тесты
pytest tests/dialogs/ -xvs

# Только window factory
pytest tests/dialogs/windows/test_window_factory.py -xvs

# Проверка что окна загружаются
python -c "from dialogs.windows import ALL_WINDOW_CONFIGS; print(len([c for c in ALL_WINDOW_CONFIGS if 'admin' in str(c.get('state'))]))"
# ✓ 8
```

## ⚙️ Регистрация новых компонентов в DI

```python
# services/conteiner/registrate/getters/admin.py

def register_dependencies(self, container: Container) -> None:
    # Getter с зависимостью на ServiceDataModel
    def build_my_getter():
        return MyGetter(model_data=container.resolve(ServiceDataModel))

    container.register(MyGetter, factory=build_my_getter, scope=punq.Scope.singleton)

    # MessageBuilder без зависимостей
    container.register(MyMessage, factory=lambda: MyMessage(), scope=punq.Scope.singleton)

    # KeyboardBuilder без зависимостей
    container.register(MyKeyboard, factory=lambda: MyKeyboard(), scope=punq.Scope.singleton)
```

## 📝 Регистрация окна в ALL_WINDOW_CONFIGS

```python
# dialogs/windows/__init__.py

admin_my_windows = [
    {
        "state": MyState.my_window,
        "message_cls": MyMessage,           # MessageBuilder класс
        "keyboard_cls": MyKeyboard,         # KeyboardBuilder класс
        "getter_cls": MyGetter,             # DataGetter класс или None
    },
]

ALL_WINDOW_CONFIGS = (
    # ... существующие окна ...
    + admin_my_windows  # Добавить новые окна
)
```

## 🐛 Типичные ошибки и решения

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `AttributeError: 'NoneType' has no attribute 'keys'` | cache_service = None | Проверить middleware_data.get("cache") |
| `KeyError: email` при cache.keys.get(key.id) | Key.id не существует | Использовать key.email |
| `TypeError: __init__() missing required argument` | Getter не зарегистрирован в DI | Добавить в AdminRegistrar |
| "Window config not found" | Окно не в ALL_WINDOW_CONFIGS | Добавить конфиг в windows/__init__.py |
| `RuntimeError: State ... not found` | Состояние не определено в states/admin.py | Добавить в AdminManager/AdminSearchManagementSG/AdminMassMailing |

## 📚 Документация

- **Полная документация:** `docs/ADMIN_DIALOGS.md`
- **Архитектура диалогов:** `docs/DIALOGS_MODULE.md`
- **CacheService:** см. CLAUDE.md "Cache Access Rules"

## 🔗 Быстрые ссылки

```python
# Импорты для работы с admin-диалогами
from dialogs.windows.widgets.message.admin import AdminMainMessage, ...
from dialogs.windows.widgets.keybord.admin import AdminMainKeyboard, ...
from dialogs.windows.getters.admin import AdminStatsGetter, ...
from getters.on_click.admin_click import on_click_all_keys, on_click_mass_mailing, ...
from getters.workers import delete_expired_keys_fast
from services.conteiner.registrate.getters.admin import AdminRegistrar
from states import AdminManager, AdminSearchManagementSG, AdminMassMailing
```

---

**Последнее обновление:** 2026-02-27
**Версия:** WindowFactory + CacheService v1.0
