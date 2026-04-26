# Анализ готовности к web/miniapp — выполнен 2026-02-22

## Критические зависимости от Telegram в бизнес-слое

### Прямые импорты aiogram в services/
1. `services/core/payment/renewal_service.py` — `from aiogram.utils.keyboard import InlineKeyboardBuilder`, `from bot_project import bot`
2. `services/core/payment/creation_service.py` — то же самое, `bot.send_message()` внутри сервиса
3. `services/notification/core.py` — `from aiogram import Bot`, `Bot` как параметр `process()`
4. `services/notification/utils/keyboard_builder.py` — `InlineKeyboardBuilder` + `InlineKeyboardButton`
5. `services/core/keys/utils/formtion.py` — `from middlewares.cache_middleware import CacheMiddleware` (неиспользуемый импорт)
6. `services/scenarios/create_first_key_scenario.py` — `from aiogram_dialog import DialogManager`, `dialog_manager.start()`

### Прямые импорты bot_project (глобальный singleton)
- `bot_project.py` создаёт `bot = Bot(...)` на уровне модуля
- `renewal_service.py` и `creation_service.py` делают `from bot_project import bot`
- Это делает эти сервисы нетестируемыми и неизолируемыми

### tg_id как единственный идентификатор пользователя
- `User.tg_id` — PRIMARY KEY в БД (int8), нет uuid/email
- Все сервисы принимают `tg_id: int`
- `ServiceDataModel.users.get_data(tg_id)` — hardcoded

## Нет протоколов для уведомлений
- `FunnelStrategy.process()` принимает `bot: Bot` — прямая зависимость
- Нет `NotificationPort` или `MessageSenderProtocol`

## DI контейнер — потенциально переиспользуемый
- `services/conteiner/app.py` — синглтон, не привязан к aiogram
- Но `services/conteiner/registrate/core/coreservice.py` создаёт `XUISession` — который 
  уже не привязан к Telegram
- Регистраторы `getters/` привязаны к `aiogram_dialog.DialogManager`

## Что чистое (переиспользуемое)
- `models/` — чистые dataclass, нет Telegram
- `database/` — asyncpg, чистый
- `services/cache/` — чистый
- `services/core/data/` — чистый
- `services/core/keys/utils/create_key.py` — чистый (только XUISession + asyncpg)
- `services/core/payment/processor.py` — чистый
- `services/core/user/` — чистый
- `services/core/segmentation/` — чистый
- `client.py` (XUISession) — чистый

## Что требует разделения для web
1. `renewal_service.py` / `creation_service.py` — извлечь `send_message` в порт
2. `notification/core.py` — `Bot` → `NotificationPort`
3. `notification/utils/keyboard_builder.py` — aiogram types → абстракция
4. `scenarios/create_first_key_scenario.py` — `DialogManager` → абстрактный `FlowController`
5. `User` — добавить `user_id: UUID` или `email` для web-идентификации
