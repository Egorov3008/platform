# Модуль диалогов (dialogs)

Этот модуль реализует систему диалогов для телеграм-бота с использованием библиотеки aiogram-dialog. Диалоги обеспечивают удобное пошаговое взаимодействие с пользователем через FSM (Finite State Machine).

## Общая архитектура

Модуль использует **два подхода** к созданию диалогов:

### Подход 1: YAML DLS (Legacy, постепенно миграция)
1. **DLS (Dialog Language Specification)** - YAML-файлы с описанием окон диалогов
2. **Лоадер** - парсирует YAML и создает Dialog-объекты
3. Используется для: профиль, ключи, платежи, регистрация, инструкции, правила

### Подход 2: WindowFactory (Modern, новый стандарт)
1. **MessageBuilder** - Python-класс для построения текста сообщения
2. **KeyboardBuilder** - Python-класс для построения клавиатуры (кнопки, TextInput, Radio)
3. **DataGetter** - Python-класс для получения данных из сервисов
4. **WindowFactory** - фабрика, создающая Window-объекты из этих компонентов
5. **DI Container** - регистрирует зависимости для инжекции

**Используется для:** Администраторские диалоги (панель, поиск, рассылка)

> 📖 **Подробная документация новой архитектуры:** см. [ADMIN_DIALOGS.md](./ADMIN_DIALOGS.md)

## Основные компоненты

### dialog_factory.py

Фабрика окон, которая:
- Создает окна диалогов на основе YAML-конфигураций
- Инжектит зависимости через DI-контейнер (punq)
- Управляет жизненным циклом компонентов окон

### loader.py

Модуль загрузки диалогов:
- Автоматически находит и загружает все DLS-файлы из папки `shema`
- Создает Dialog-объекты из YAML-конфигураций
- Игнорирует файлы с префиксом `_` или `.`

### setup.py

Модуль инициализации диалогов (содержимое не доступно)

## Структура директорий

### shema/

Содержит YAML-файлы с описанием диалогов:

- **user/** - диалоги для пользователей
  - gift/ - диалоги подарков
  - keys/ - диалоги управления ключами
  - payments/ - диалоги оплаты
  - profile/ - диалоги профиля
  - registration/ - диалоги регистрации
  - rules/ - диалоги правил использования
  - tariff/ - диалоги тарифов

- **admin/** - диалоги для администраторов
  - key_manager/ - управление ключами
  - main/ - основная панель
  - mass_mailing/ - массовая рассылка
  - search/ - поиск пользователей
  - user_manaer/ - управление пользователями

- **partials/** - частичные компоненты, которые можно включать в другие диалоги
  - buttons/ - шаблоны кнопок
  - conditions.yaml - условия отображения
  - messages.yaml - шаблоны сообщений

### windows/

Компоненты для построения окон диалогов:

- **base.py** - базовые абстрактные классы:
  - `DataGetter` - абстрактный класс для получения данных
  - `MessageBuilder` - абстрактный класс для построения сообщений
  - `KeyboardBuilder` - абстрактный класс для построения клавиатур
  - `GenericSelectBuilder` - универсальный билдер для создания Select-клавиатур

- **window_factory.py** - фабрика окон, создающая Window-объекты
- **form.py** - базовый класс формы
- **getters/** - реализации DataGetter для различных сценариев
- **widgets/** - реализации MessageBuilder и KeyboardBuilder

### messages/

Шаблоны сообщений для различных сценариев:

- **users/** - сообщения для пользователей
  - error_msg/ - сообщения об ошибках
  - gift/ - сообщения о подарках
  - instructions/ - инструкции по установке
  - payments/ - сообщения об оплате
  - profile/ - сообщения профиля
  - reminder/ - напоминания
  - rules/ - правила использования
  - tariff/ - сообщения о тарифах
  - welcom/ - приветственные сообщения

- **stats.py** - сообщения статистики

### admin/

Диалоги и компоненты для администраторской панели:

- **adminpanel.py** - основная панель администратора
- **admin_key_manager.py** - управление ключами
- **admin_registration.py** - регистрация пользователей
- **admin_user_profile.py** - профиль пользователя
- **mass_mailing.py** - массовая рассылка
- **search_dialog.py** - поиск пользователей

## Пример DLS-конфигурации

Пример диалога подарков (gift_flow.yaml):

```yaml
windows:
  - state: GiftStates.main
    text: |
      🎁 <b>Подарите VIP-доступ другу!</b>

      Отправьте ему эту ссылку — и он получит <b>тариф «160»</b> на целый месяц
      ✅ Подарок активируется автоматически при регистрации
      ⏰ Действует только для нового пользователя

      👇 Нажмите, чтобы скопировать ссылку и отправить другу:
    buttons:
      - type: copy
        text: "📋 Скопировать ссылку"
        value: "{link}"
      - !include ../partials/buttons/profile.yaml
    getter: GiftStates.main
```

## Регистрация диалогов

Основные диалоги регистрируются в `__init__.py`:

```python
from aiogram import Router
from aiogram_dialog import Dialog

from .windows import profile, tariff, gift, payment

dialog_profile = Dialog(*profile)
dialog_tariff = Dialog(*tariff)
dialog_gift = Dialog(*gift)
dialog_payment = Dialog(*payment)

router: Router = Router(name="dialog")
router.include_routers(
    dialog_profile,
    dialog_tariff,
    dialog_gift,
    dialog_payment,
)
```

## Преимущества архитектуры

1. **Декларативность** - интерфейс описывается в YAML, что делает его легко читаемым
2. **Модульность** - компоненты легко переиспользуются через partials
3. **DI-поддержка** - зависимости инжектятся через контейнер, что упрощает тестирование
4. **Гибкость** - легко добавлять новые диалоги без изменения основного кода
5. **Поддержка условий** - возможность показывать/скрывать элементы на основе условий

## Использование

Для создания нового диалога:

1. Создать YAML-файл в соответствующей директории в `shema/`
2. Описать окна, состояния, кнопки и геттеры
3. При необходимости создать реализации DataGetter, MessageBuilder, KeyboardBuilder
4. Добавить сообщения в соответствующий файл в `messages/`

Система автоматически загрузит и зарегистрирует новый диалог при запуске бота.

## Best Practices

1. Используйте partials для переиспользуемых компонентов (кнопки, условия)
2. Разделяйте диалоги по функциональности (пользовательские и админские)
3. Используйте осмысленные имена для состояний и компонентов
4. Документируйте сложные логики в комментариях к YAML-файлу
5. Тестируйте диалоги на всех возможных путях выполнения

## Новые администраторские диалоги (WindowFactory)

Администраторские диалоги реализованы с использованием современной архитектуры **MessageBuilder + KeyboardBuilder + DataGetter**:

### Структура

```
dialogs/windows/
├── widgets/
│   ├── message/admin/        ← Сообщения (panel, search, mailing)
│   └── keybord/admin/        ← Клавиатуры (panel, search, mailing)
├── getters/admin/            ← Получение данных (panel, mailing)
└── __init__.py               ← Регистрация окон (8 новых окон)

services/conteiner/registrate/getters/
└── admin.py                  ← DI регистрация (AdminRegistrar)

getters/
├── on_click/admin_click.py   ← Обработчики кнопок (с CacheService)
└── workers.py                ← Фоновые функции (delete_expired_keys_fast)
```

### Диалоги (8 окон)

**Панель администратора (3 окна):**
- AdminManager.main → выбор функции (статистика, поиск, рассылка, синхронизация)
- AdminManager.static_user → статистика и управление ключами
- AdminManager.confirmation_deletion_keys → подтверждение удаления просроченных

**Поиск (3 окна):**
- AdminSearchManagementSG.main → выбор метода поиска
- AdminSearchManagementSG.search_tg_id → TextInput для поиска по ID
- AdminSearchManagementSG.search_email → TextInput для поиска по email

**Рассылка (2 окна):**
- AdminMassMailing.receiving_message → ввод текста сообщения
- AdminMassMailing.confirmation → выбор режима (закрепить/не закреплять) и отправка

### Ключевые особенности

✅ **Type-safe** — полная поддержка типов Python
✅ **CacheService** — используется вместо legacy cache_instance
✅ **DI Container** — зависимости инжектятся автоматически
✅ **Testable** — каждый компонент можно тестировать отдельно
✅ **No YAML** — конфигурация в Python, компилируется статически

**📖 Подробная документация:** [ADMIN_DIALOGS.md](./ADMIN_DIALOGS.md)

---

## Миграция с YAML DLS на WindowFactory

### Процесс миграции

1. **Оцените диалог** — YAML-файл, states, обработчики
2. **Создайте компоненты:**
   - MessageBuilder — текст сообщения
   - KeyboardBuilder — кнопки и действия
   - DataGetter (если нужен) — получение данных
3. **Зарегистрируйте в DI** — создайте Registrar-класс
4. **Добавьте в ALL_WINDOW_CONFIGS** — окна в windows/__init__.py
5. **Обновите обработчики** — используйте CacheService вместо legacy services

### Пример: миграция админ-панели

**Было (YAML):**
```yaml
# dialogs/shema/admin/main/adminpanel_flow.yaml
windows:
  - state: AdminManager.main
    text: "🤖 Панель администратора"
    buttons:
      - text: "📊 Статистика"
        action: switch_to
        state: AdminManager.static_user
```

**Стало (WindowFactory):**
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

### Преимущества WindowFactory

| Критерий | YAML DLS | WindowFactory |
|----------|----------|---------------|
| Type Safety | ❌ Нет | ✅ Полная |
| IDE Support | ❌ Нет | ✅ Да (goto, rename, etc.) |
| Testing | ⚠️ Сложно | ✅ Легко |
| Static Analysis | ❌ Нет | ✅ Да (mypy, pylint) |
| Refactoring | ⚠️ Вручную | ✅ Автоматически |
| Performance | ⚠️ Runtime parsing | ✅ Pre-compiled |
| Documentation | ❌ Неявная | ✅ В коде |

---

Документация создана на основе анализа структуры кода и файлов модуля dialogs.

**Последнее обновление:** 2026-02-27
**Версия архитектуры:** WindowFactory + CacheService v1.0