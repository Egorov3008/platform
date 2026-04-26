# Архитектурные паттерны — Bot 3xui

## Ключевые файлы

- DI контейнер: `services/conteiner/app.py:get_container()`
- Двухуровневый доступ к данным: `services/core/data/base.py:BaseData[T]`
- Базовый репозиторий БД: `database/base.py:BaseRepository[T]`
- Ключи кеша: `services/cache/key_manager.py:CacheKeyManager`
- Admin DI регистрар: `services/conteiner/registrate/getters/admin.py:AdminRegistrar`
- Оркестратор воронок: `services/notification/manager.py:FunnelManager`

## Системная проблема: `_name` в моделях (РЕШЕНА 2026-02-22)

Решение: `_name: ClassVar[str] = "..."` (ClassVar игнорируется asdict).
Образец правильного подхода: `Key._DB_FIELDS` whitelist в `models/keys/key.py`.

## Паттерн: SERIAL поля и `to_dict()` (обнаружен 2026-02-22)

Решение: `_DB_FIELDS: ClassVar[frozenset]` whitelist в `to_dict()` — исключить `id`.

## Cache Key Rules (подтверждено)

- Key → email, Inbound → (server_id, inbound_id), PaymentModel → payment_id
- Остальные → id или tg_id по типу модели

## Мёртвые файлы (ветка user_system, 2026-03-04)

- `dialogs/partner_dialog.py` — не используется, импортирует `from state import PartnerProgram` (модуль `state.py` не существует — только `states/`)
- `widgets/keybord.py` — используется только в `dialogs/windows/widgets/keybord/admin/user_profile.py:key_selector`
- Legacy-функции в `getters/on_click/admin_click.py` — см. patterns.md

## Cross-layer coupling (критично)

`services/core/segmentation/manager.py:3` импортирует `from services.notification.core import UserSegmenter`.
Слой `core` зависит от `notification` — нарушение инверсии зависимостей.
Дубликат `UserSegmenter` уже есть в `services/core/segmentation/ruls.py` — нужно переключить.

## Воронки уведомлений — НЕ РАБОТАЮТ в production (2026-03-04)

`tasks.py`: `start_sync_cache` и `start_notification_bot` ЗАКОММЕНТИРОВАНЫ.
`FunnelManager.run_cycle()` не вызывается нигде. Воронки мертвы.
Для деталей — см. patterns.md.

## TypeError в GiftActivationScenario._process_success() (2026-03-04)

`services/scenarios/gift_scenario.py:106`:
`cache.gifts.temporary_set(key, **data)` — пропущен обязательный параметр `ttl: timedelta`.
TypeError в runtime при активации подарочного ключа.

## Баги в handlers/notifications.py (актуально 2026-03-09)

1. `handle_activate_stock`, строка 107: `tg_id = dialog_manager.event.from_user.id` —
   `middleware_data` уже исправлен (используется `.get()`). Текущая проблема:
   `dialog_manager.event` типизирован как `ChatEvent` (Union из 5 типов), IDE не может
   гарантировать `.from_user`. Нужно использовать `query.from_user` — он уже есть в сигнатуре.
   Дополнительно: `query.from_user` типизирован как `User | None` — нужна проверка.

2. `handle_renew_key`, строка 57: `key.tariff_id == default_plan` — ИСПРАВЛЕНО,
   теперь `int(DEFAULT_PRICING_PLAN)`. Но проверка key на None добавлена (строка 51-54).

## CreateFerstKeyScenario — системные баги (2026-03-09)

Файл: `services/scenarios/create_first_key_scenario.py`

1. Строка 133: `tariff_id = self._gift.tariff_id if self._gift else DEFAULT_PRICING_PLAN`
   `DEFAULT_PRICING_PLAN` — тип `str | None`. Передаётся в `tariff_data.get_data(tariff_id)`.
   Если тариф не найден → `_tariff = None` → строка 72: `self._tariff.id` → AttributeError.
   Это РЕАЛЬНАЯ причина ошибки "установки пробного периода".
   Фикс: `int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10`

2. Строки 30-37: `dialog_manager=None` в конструкторе, присваивается вручную после DI-resolve.
   Если сценарий зарегистрирован как singleton — гонка данных при конкурентных вызовах.
   Нужно проверить scope в DI-регистраре.

3. Строка 123 (`get_data`): параметр `tg_id` в `start(tg_id, server_id)` игнорируется —
   пользователь берётся из `dialog_manager.event.from_user.id`. Мёртвый аргумент.

4. Строка 138: `_conn` из конструктора перезаписывается в `get_data()` из middleware.
   Два источника одного соединения — архитектурное рассогласование.

## Семантическая ошибка в routing.py (2026-03-09)

`KEY_SEGMENT_TO_FUNNEL` маппит `KeySegment.TRIAL → "trial_unused"`, но
`TrialCondition` (key_ruls.py:76) возвращает True для любого ключа с `tariff_id == 10`,
включая активно используемые trial-ключи. Воронка `trial_unused` должна получать только
неиспользуемые trial-ключи, но фильтр сегментатора не учитывает `used_traffic`.
Дополнительная фильтрация есть в `TrialReminderFunnel.should_send()`, но
сегментатор классифицирует их неверно — они попадают в TRIAL вместо нужного UNUSED.

## Критические баги в TrialReminderFunnel (обнаружено 2026-03-09)

Файл: `services/notification/funnels/trial_reminder.py`

1. **Строка 48: NameError в runtime** — `next([...])` вызывается на list, а не на iterator.
   `next()` принимает iterator; список вернёт `list`, а не первый элемент.
   Результат: `TypeError: 'list' object is not an iterator` при каждом вызове `process()`.
   Фикс: убрать list comprehension внутрь генераторного выражения без `[]`.

2. **Строка 53: NameError `lint_key`** — опечатка: `lint_key` вместо `link_key`.
   `link_key` определён строкой выше (строка 50). Результат: `NameError` в runtime.

3. **Строка 52-53: несоответствие сигнатуры** — `_build_text()` определён как `_build_text(email: str)`
   (строка 70), но вызывается как `self._build_text()` без аргументов → `TypeError: missing argument`.

4. **Строка 84: некорректный CopyTextButton** — `kb.button(copy_text=link_key)` передаёт
   объект `CopyTextButton` как значение параметра `copy_text`. Правильный параметр aiogram —
   `copy_text` принимает `CopyTextButton` объект, но кнопка создана в строке 50, а не используется
   как параметр `copy_text=link_key.text`. Нужна проверка реального API aiogram.

5. **Строка 40 vs строка 83 UnusedCondition**: `should_send()` проверяет `used_traffic == 0.0`,
   а `UnusedCondition.check_key()` (key_ruls.py:83) проверяет `total_gb == 0.0`. Разные поля!
   `total_gb: Optional[int]` — лимит трафика (default=10); `used_traffic: Optional[float]` — реальный
   расход. Оба не None по умолчанию. Логика `should_send()` корректна (used_traffic), но
   `UnusedCondition` проверяет лимит, а не расход — это семантическая ошибка сегментатора.

## Статус tasks.py (актуализировано 2026-03-09)

`start_sync_cache` и `start_notification_bot` НЕ закомментированы — оба вызываются
из `start_all_tasks()`. Воронки технически работают. Предыдущая запись в MEMORY.md устарела.

## DEFAULT_PRICING_PLAN — тип str, не int (подтверждено 2026-03-09)

`config.py:62`: `DEFAULT_PRICING_PLAN = os.getenv("DEFAULT_PRICING_PLAN")` — тип `str | None`.
В коде используется для сравнения с `key.tariff_id: Optional[int]`.
Все прямые сравнения `== DEFAULT_PRICING_PLAN` без int() — скрытые семантические баги.
