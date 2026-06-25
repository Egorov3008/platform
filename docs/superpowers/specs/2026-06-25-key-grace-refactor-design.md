# Рефакторинг флоу создания/продления ключей: модель Client с grace-неделей

**Дата:** 2026-06-25
**Статус:** дизайн (awaiting implementation plan)

## Контекст и цель

В панели 3x-UI создан inbound `7` (`XUI_INBOUND_ID_LANDING`) — доступ только к Telegram.
Сегодня:
- платный ключ создаётся на `AVAILABLE_CONNECTIONS` (`[11,12]`) — полный VPN;
- landing-ключ — отдельный 24ч анонимный клиент на inbound `7`;
- продление лишь extends `expiryTime` того же клиента; никакой концепции «даунгрейда по истечении подписки» нет.

Цель рефакторинга — ввести единую модель `Client` (объект панели = `Key` в БД): один 3x-ui
клиент, агрегирующий несколько inbound через `attach`/`detach`. Платная подписка держит
`[7] + AVAILABLE_CONNECTIONS`; при истечении подписки `AVAILABLE_CONNECTIONS` снимаются, а
inbound `7` остаётся на неделю (grace) — telegram-only окно для продления. После grace клиент
удаляется; восстановление — только новой оплатой (новый ключ).

## Зафиксированные решения (из брейншторма)

1. **Client (панель) = Key (БД).** Модель «один Key = один 3x-ui клиент» сохраняется; у юзера
   может быть несколько ключей. Агрегация inbound — через panel API `attach`/`detach`.
2. **Inbound `7` всегда в `inbound_ids` ключа** (базовый постоянный inbound).
   `AVAILABLE_CONNECTIONS [11,12]` — динамический оверлей по оплате.
3. **Trial-ключ = полный VPN `[7,11,12]`** (как сейчас); grace/unpaid-логика применяется
   только при истечении подписки (trial — тоже подписка).
4. **Grace планируется заранее:** при создании/продлении подписочного ключа пишется
   `grace_expiry = expiry + GRACE_PERIOD_DAYS`. Переход active→grace делает scheduler.
5. **Продление во время grace** — re-attach `[11,12]` на тот же клиент, новый `expiry` +
   `grace_expiry`, статус `active`.
6. **Landing = будущий Client:** landing-ключ (`[7]`) того же юзера при claim/первой оплате
   апгрейдится attach'ем `[11,12]` к тому же клиенту (Happ-URL сохраняется).
7. **Подход A:** derived-статус + выделенный `GraceManager` + scheduler-переходы с
   идемпотентной reconciliation.
8. **Предустановка панельного `expiryTime = grace_expiry`** (а не `expiry_time`): клиент живёт
   всё grace-окно; переход active→grace = только `detach [11,12]`, без race по времени.

## Модель данных и статус

### Новая колонка
`keys.grace_expiry BIGINT` (ms, nullable). `NULL` — у ключа нет grace (landing-24h, free
non-subscription keys, старые уже-истёкшие).

Поле `grace_expiry: Optional[int] = None` в `Key` dataclass (`backend/models/keys/key.py`) +
добавить в `_DB_FIELDS`.

### Статус — производный (без колонки)
Хелпер `KeyStatus.of(key, now_ms) -> str` (новый модуль
`backend/services/core/keys/utils/status.py`):

| Статус | Условие |
|---|---|
| `active` | `grace_expiry is not None and now < expiry_time` |
| `grace` | `grace_expiry is not None and expiry_time <= now < grace_expiry` |
| `expired` | `grace_expiry is not None and now >= grace_expiry` |
| `none` | `grace_expiry is None` (landing-24h / free — своя логика; `expiry_time < now` трактуется как expired) |

### Inbound-наборы (панель = source of truth, в БД не хранится)
`backend/services/core/keys/utils/inbounds.py`:
```
BASELINE_INBOUNDS     = [XUI_INBOUND_ID_LANDING]   # [7] — всегда
PAID_OVERLAY_INBOUNDS = AVAILABLE_CONNECTIONS     # [11,12]
paid_inbound_ids()  -> [7,11,12]   # active/trial
grace_inbound_ids() -> [7]         # grace
expired_inbound_ids() -> []        # expired
expected_inbound_ids(status) -> по статусу
```

### Env
`backend/config.py` + `.env`:
- `GRACE_PERIOD_DAYS` (default `7`) — длительность grace.
- Переиспользуются `XUI_INBOUND_ID_LANDING`, `AVAILABLE_CONNECTIONS`.

## Сервис `GraceManager`

`backend/services/core/keys/utils/grace.py`. Зависимости: `XUISession`,
`ServiceDataModel`, `CacheService`. Не знает про scheduler/HTTP.

### Низкоуровневый метод на `XUISession`
```
async def set_inbounds(self, email, target_inbound_ids: list[int]) -> bool
    # fetch PanelClient, diff: attach недостающие, detach лишние. Идемпотентен.
```
Поверх существующих `attach`/`detach`/`update`. `extend_client_key` остаётся (только
`expiryTime`+`enable`).

### Методы `GraceManager`

| Метод | Панель | БД/кеш |
|---|---|---|
| `enter_grace(key)` | `set_inbounds([7])` | без изменений в БД (статус сам становится `grace`); `cache` refresh |
| `expire_after_grace(key)` | `set_inbounds([])` + `delete(email)` | строка остаётся (история); `cache` инвалид |
| `renew_from_grace(key, tariff, months)` | `set_inbounds([7,11,12])` + `update expiryTime=grace_expiry, enable=True` | `expiry_time=new_expiry`, `grace_expiry=new_expiry+GRACE`, сброс `notified_*`; `cache` |
| `upgrade_from_landing(key, tariff, months)` | `set_inbounds([7,11,12])` + `update expiryTime=grace_expiry, enable=True` | перенос `tg_id`, `tariff_id`, `expiry_time=new_expiry`, `grace_expiry=new_expiry+GRACE`, `limit_ip`; `cache` |
| `reconcile(key)` | `set_inbounds(expected_inbound_ids(KeyStatus.of(key)))` | no-op в БД — только панель |

### Идемпотентность и устойчивость
- `set_inbounds` берёт текущее состояние панели → корректен при повторах.
- Частичный провал (attach прошёл, detach упал) → промежуточное состояние; `reconcile` на
  следующем прогоне доведёт. Логируется, не падает.
- `expire_after_grace`: detach all → затем `delete`; при 404 на `delete` считать уже удалённым
  (как `XUISession.delete_client`).
- Статус из БД — арбитр; панель подгоняется под него.

## Флоу создания/продления/landing

| Флоу | Изменения |
|---|---|
| **A. Платный ключ (первая оплата, нет ключа)** | `FormationKey.form_new_key`: `inbound_ids = paid_inbound_ids()`, `grace_expiry = expiry + GRACE_DAYS`; `is_subscription` → true. `add_client` принимает список. Панельный `expiryTime = grace_expiry`. |
| **B. Trial `/keys/trial`** | `inbound_ids = paid_inbound_ids()`, `grace_expiry = expiry + GRACE_DAYS`. `expiryTime = grace_expiry`. |
| **C. Landing 24h `/landing/quick-key`** | без изменений: `[7]`, `grace_expiry = None`, pseudo tg_id, `limit_ip=1`. |
| **D. Landing claim (НОВЫЙ юзер)** | вместо `extend_client_key` → `GraceManager.upgrade_from_landing`: перенос tg_id, `set_inbounds([7,11,12])`, trial `expiry`, `grace_expiry`, `enable=True`. Тот же email/Happ-URL. |
| **E. Первая оплата юзера с landing-ключом `[7]`** | `KeyCreationService` перед созданием ищет landing-origin ключ юзера (`landing_uid` set, `converted_tg_id==tg_id`, inbound `[7]`, `grace_expiry is None`). Найден → `upgrade_from_landing`. Не найден → `CreateKey` (A). |
| **F. Продление active** | `KeyRenewal.extension_key` дополнительно: `grace_expiry = new_expiry + GRACE_DAYS`, `reconcile` (вернуть `[11,12]` если уплыли), `update expiryTime = grace_expiry` в панели. |
| **G. Продление во время grace** | `KeyRenewalService`/`PaymentRouter` по `KeyStatus.of(key)`: `grace` → `GraceManager.renew_from_grace`; `expired` → отказ (новый ключ). |
| **H. mark-converted (СУЩЕСТВУЮЩИЙ юзер)** | без изменений: landing-24h teaser на pseudo tg_id, до 24ч, без upgrade. |

**Признак подписки** (`FormationKey`): `is_subscription = tariff.amount > 0 or tariff.id == DEFAULT_PRICING_PLAN`. Только тогда пишется `grace_expiry` и панельный `expiryTime = grace_expiry`; иначе `grace_expiry = None`, `expiryTime = expiry_time`.

## Scheduler-переходы + reconciliation

**Предустановка `expiryTime`:** при создании/продлении подписочного ключа панельный
`expiryTime = grace_expiry`. Тогда:
- `active → grace` = только `detach [11,12]` (клиент уже живёт до `grace_expiry`), без race.
- `grace → expired` при `now ≥ grace_expiry`: клиент сам отключается панелью; мы `delete`/disable.

**Новый job `grace_transitions`** (cadence — раз в час, в начале `run_notifications` в
`backend/background/scheduler.py`):
```
для каждого ключа с grace_expiry is not None:
    reconcile(key)   # приведёт inbound-набор к ожидаемому по статусу
```
`enter_grace`/`expire_after_grace` — частные случаи `reconcile` (по статусу).

**Reconciliation в `panel_sync` (3ч):** в `DatabaseSynchronizer.sync_data` добавить шаг
`GraceManager.reconcile` для каждого известного ключа — лечит дрейф от упавших ранее
attach/detach. Двойное покрытие с часовым job'ом.

**Race с оплатой:** если плата приходит в момент grace-перехода, `expiry_time` в БД уже
обновлён продлением → статус `active` → `reconcile` не detacht.

## Миграция, env, граничные случаи

**DB-миграция:**
```sql
ALTER TABLE keys ADD COLUMN grace_expiry BIGINT;
```

**Backfill** (`scripts/migrate_grace.py`, идемпотентный, `--dry-run`): для активных
платных/trial ключей с `grace_expiry IS NULL`:
1. `set_inbounds([7,11,12])` (attach 7 если нет).
2. `grace_expiry = expiry_time + GRACE_DAYS*86400000` → БД.
3. `update expiryTime = grace_expiry` в панели.
Старые уже-истёкшие ключи без grace не трогаем.

**Env:** `GRACE_PERIOD_DAYS` (default 7); `XUI_INBOUND_ID_LANDING`, `AVAILABLE_CONNECTIONS` — reuse.

**Граничные случаи:**

| Случай | Поведение |
|---|---|
| `grace_expiry IS NULL` и `expiry_time < now` | `none`-статус → expired (старое поведение, без grace). |
| Бесплатный `/keys/create` (non-trial free tariff) | `grace_expiry = None`; умирает по `expiry_time` без grace. |
| Trial (тариф `DEFAULT_PRICING_PLAN`) | grace применяется (trial — подписка). |
| Landing-24h (pseudo tg_id, `[7]`, `grace_expiry None`) | не подписка; 24ч; upgrade на claim/оплате. |
| Несколько ключей у юзера | модель сохраняется; landing-upgrade ищет по `landing_uid`+`converted_tg_id==tg_id`+`[7]`+`grace_expiry None`. |
| `reconcile` натыкается на 404 в панели | `expire_after_grace`-путь: считать удалённым, зачистить БД-строку. |
| Плата в момент grace-перехода | статус из БД = арбитр; `reconcile` не detacht. |

## Тестирование

По паттерну `AsyncMock` для `asyncpg`, `XUISession`, `yookassa`.

**Юнит-тесты (`backend/tests/`):**
- `KeyStatus.of` — 4 состояния + граничные `==`.
- `GraceManager`: `enter_grace`, `expire_after_grace` (идемпотентен на 404), `renew_from_grace`,
  `upgrade_from_landing`, `reconcile` (дрейф-сценарии: `[7,11,12]`+grace→detach; `[7]`+active→attach; совпало→no-op).
  Мок `XUISession.set_inbounds/update/delete` + `service_data.keys.update` + `cache`.
- `FormationKey.form_new_key`: `inbound_ids == paid_inbound_ids()` для paid; `[7]` для
  landing-override; `grace_expiry` выставлен для подписки, `None` для free/landing.
- `KeyRenewalService`/`KeyRenewal` ветвление: active→`extension_key`+`grace_expiry`; grace→`renew_from_grace`; expired→отказ.
- `KeyCreationService` landing-upgrade: есть landing-ключ `[7]`→`upgrade_from_landing`; нет→`CreateKey`.
- `landing.claim_key`: `set_inbounds([7,11,12])` + trial `expiry` + `grace_expiry`, email сохранён.
- Job `grace_transitions`: ключи на границах → правильный `GraceManager`; повтор идемпотентен;
  race с одновременной оплатой.
- `panel_sync` reconcile-шаг: схождение inbound-набора.

**Интеграционные:** TestClient + `app.dependency_overrides[get_service_data]` — webhook оплаты →
active→grace по таймеру; продление во время grace → active.

## Файлы (затрагиваемые)

- `backend/models/keys/key.py` — поле `grace_expiry` + `_DB_FIELDS`.
- `backend/services/core/keys/utils/status.py` — НОВЫЙ `KeyStatus`.
- `backend/services/core/keys/utils/inbounds.py` — НОВЫЙ хелперы inbound-наборов.
- `backend/services/core/keys/utils/grace.py` — НОВЫЙ `GraceManager`.
- `backend/services/core/keys/utils/formtion.py` — `paid_inbound_ids()`, `grace_expiry`, `is_subscription`.
- `backend/services/core/keys/utils/renewal.py` — `grace_expiry` + reconcile.
- `backend/services/core/keys/utils/create_key.py` — передача `paid_inbound_ids()`.
- `backend/client.py` — `XUISession.set_inbounds`.
- `backend/services/core/payment/creation_service.py` — landing-upgrade ветвление.
- `backend/services/core/payment/renewal_service.py` — ветвление по статусу.
- `backend/api/v1/landing.py` — `claim_key` через `upgrade_from_landing`.
- `backend/background/scheduler.py` — job `grace_transitions`.
- `backend/services/synchron/*` — reconcile-шаг в `panel_sync`.
- `backend/config.py` + `.env` — `GRACE_PERIOD_DAYS`.
- `scripts/migrate_grace.py` — НОВЫЙ backfill.
- DB-миграция (`ALTER TABLE keys`).
- `backend/tests/` — НОВЫЕ тесты.