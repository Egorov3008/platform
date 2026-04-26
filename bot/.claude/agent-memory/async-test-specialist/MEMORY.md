# Async Test Specialist — Project Memory

## Project Stack
- Python 3.10, pytest-asyncio `asyncio_mode=auto`
- asyncpg for PostgreSQL, aiogram 3 + aiogram-dialog
- punq DI container (`conteiner/` — intentional legacy spelling)

## Critical: BaseRepository Mock Setup

`BaseRepository._acquire()` checks `isinstance(pool, asyncpg.Pool)`.
- If Pool: calls `pool.acquire()` → async context manager chain
- If Connection (not Pool): uses `_ConnectionWrapper` directly

**WRONG** (causes `AsyncMock.keys() returned a non-iterable` and other failures):
```python
mock_conn = AsyncMock(spec=asyncpg.Pool)  # Pool → acquire() chain breaks assertions
result = await repository.get(mock_conn, id=1)
```

**CORRECT**: Pass a plain AsyncMock (no spec=asyncpg.Pool) so the Connection path is used:
```python
conn = AsyncMock()  # Not spec=asyncpg.Pool → _ConnectionWrapper branch → works
result = await repository.get(conn, id=1)
```

See `/home/claude/bot_3xui/tests/database/test_base_repository.py`.

## Stage 8 _DB_FIELDS Pattern (models/)

Models with `_DB_FIELDS: ClassVar[frozenset]` — `to_dict()` filters via it:
- `PaymentModel` — excludes `id` (SERIAL), keeps: payment_id, tg_id, amount, payment_type, status, created_at
- `GiftLink` — excludes `id` AND `_status`, keeps: sender_tg_id, tariff_id, token, created_at, recipient_tg_id, email, used_at
- `ReferralLink` — excludes `id`, keeps: referrer_tg_id, token, created_at
- `ReferralRedemption` — excludes `id`, keeps: referral_link_id, referred_tg_id, redeemed_at
- `ReferralReward` — excludes `id`, keeps: referrer_tg_id, reward_type, reward_value, awarded_at, is_claimed
- `Key` — original pattern, no id field at all

**`_name: ClassVar[str]`** — never appears in `asdict()` output (Python excludes ClassVars).
**`_status` in GiftLink** — instance field with `_` prefix — DOES appear in `asdict()`, excluded via `_DB_FIELDS`.
**`from_dict(data)` accepts `id`** from SELECT — all models with Optional[int] id field handle this correctly.
**`from_dict(data)` rejects `status` key** — GiftLink has no `status` dataclass field, only `_status`.

Tariff and Server have no `_DB_FIELDS` — `to_dict()` includes `id` (correct, id not SERIAL there).

## Pre-existing Broken Tests (do not fix without user request)

`tests/test_database/test_repositories.py::TestDataServiceRepositories` — 6 tests error at setup:
fixtures `mock_user`, `mock_key`, `mock_server`, `mock_payment`, `mock_tariff`, `mock_inbound_full`
don't exist in conftest (conftest has `user`, `key`, `server`, `payment`, `tariff`, `inbound_full`).
These tests also use bare variable names (`key`, `server`, etc.) instead of fixture params — dead code.

## DI Container Testing Pattern (punq, Stage 6)

`create_container()` in `services/conteiner/__init__.py` calls `create_db_pool()` — must be patched:
```python
with patch("services.conteiner.create_db_pool", return_value=mock_pool):
    container = await create_container()
```

`mock_pool = AsyncMock(spec=asyncpg.Pool)` — safe for container registration (Pool is registered as instance, not resolved via factory).

**Two fixture tiers:**
- `full_container` — full `create_container()` run (all registrars, real DI chain)
- `bare_container` — manual minimal setup (CacheStorage + CacheService + ServiceDataModel + DataService + Pool) for testing individual registrars in isolation

**Singleton identity checks use `is` not `==`:**
```python
assert container.resolve(CacheService) is container.resolve(CacheService)
```

**Registrar dependency order matters** — registrars are not independent:
- `ScenarioKeyRegistrar` needs: Core + Gift + Key + User registrars first
- `ProfileRegistrar` needs: Core + Gift + Key + User + Tariff + Scenario + Registration
- `KeysRegistrar` needs: Core + Gift + Key + User + Tariff + Scenario

Test file: `tests/services/conteiner/test_di_container.py` (36 tests, all passing)

## Key Test Files (Stage 8)

| File | Purpose |
|------|---------|
| `tests/models/test_db_fields_pattern.py` | _DB_FIELDS + _name patterns across all Stage 8 models |
| `tests/models/test_referral_models.py` | ReferralLink, ReferralRedemption, ReferralReward full coverage |
| `tests/services/gift/test_gift_link_model.py` | GiftLink — fixed to_dict/from_dict assertions |
| `tests/database/test_base_repository.py` | Fixed BaseRepository mock setup (Connection not Pool) |

## Admin Panel Tests (Stage 9 — 79 tests, all passing)

| File | Tests | Components |
|------|-------|-----------|
| `tests/dialogs/getters/admin/test_admin_stats_getter.py` | 14 | AdminStatsGetter, AdminConfirmDeleteGetter |
| `tests/dialogs/getters/admin/test_admin_keys_list_getter.py` | 23 | AdminKeyListGetter, AdminKeyDetailsGetter |
| `tests/dialogs/getters/admin/test_admin_user_profile_getter.py` | 11 | AdminUserProfileGetter |
| `tests/dialogs/getters/admin/test_mailing_confirm_getter.py` | 4 | MailingConfirmGetter |
| `tests/dialogs/getters/admin/test_key_segmentation_report.py` | 13 | KeySegmentationReportGetter (3 methods) |
| `tests/dialogs/keyboards/admin/test_admin_key_details_keyboard.py` | 14 | AdminKeyDetailsKeyboard handlers |

### Admin Test Patterns

**KeySegmentationService — never mock it.** It is pure Python. Only mock `model_data.keys.get_all()`.

**KeySegmentationReportGetter** reads cache from `middleware_data["cache"]`, not from constructor.
Mock pattern:
```python
cache = AsyncMock()
cache.keys = AsyncMock()
cache.keys.all = AsyncMock(return_value=keys)
manager.middleware_data["cache"] = cache
```

**AdminKeyDetailsKeyboard handlers** are `@staticmethod` async methods — call directly:
```python
await AdminKeyDetailsKeyboard._on_delete_key(callback, None, manager)
```

**Relative time helper for key tests:**
```python
def make_key(email, tg_id, expiry_offset_ms):
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(email=email, tg_id=tg_id, client_id="c1", key="k",
               inbound_id=1, expiry_time=now_ms + expiry_offset_ms)
```
Negative offset = expired; positive offset = active.

**AdminKeyDetailsGetter** has NO constructor args — instantiate as `AdminKeyDetailsGetter()`.
**MailingConfirmGetter** has NO constructor args — instantiate as `MailingConfirmGetter()`.
**KeySegmentationReportGetter** has NO constructor args — instantiate as `KeySegmentationReportGetter()`.

**AdminConfirmDeleteGetter** normalises single Key (not list) from `get_all()` — test both list and non-list returns.

**BaselineTestCount (pre-admin-tests):** 25 failed / 572 passed / 45 errors (pre-existing failures, do not fix without request).

## Notification Module Tests (Stage 10 — 113 tests, all passing)

| File | Tests | Purpose |
|------|-------|---------|
| `tests/services/notification/test_user_segmenter.py` | 31 | UserSegmenter + 4 condition factories |
| `tests/services/notification/test_models.py` | 14 | NotificationResult, FunnelRunReport |
| `tests/services/notification/test_rate_limiter.py` | 9 | RateLimiter.send_message_safe() |
| `tests/services/notification/test_cache_helpers.py` | 9 | NotificationDedupeCache |
| `tests/services/notification/test_manager.py` | 18 | FunnelManager |
| `tests/services/notification/test_funnels.py` | 32 | All 4 funnels |

**core.py was updated** to add condition factories and full `UserSegmenter` with `segment_rules`.

### Critical: datetime mock in core.py (mixed naive/aware)

`inactive_trial_condition` uses `datetime.now(timezone.utc)` (UTC-aware).
`expiring_keys_condition` uses `datetime.now()` (naïve).
Under the same `patch("services.notification.core.datetime")`, use `side_effect`:
```python
def _now_side_effect(tz=None):
    return utc_aware_datetime  # works for both; .timestamp() works on both types
mock_dt.now.side_effect = _now_side_effect
mock_dt.fromtimestamp = datetime.fromtimestamp  # preserve real fromtimestamp
```

### Critical: _FIXED_NOW_MS must match mock's datetime.now()

```python
# CORRECT — naïve .timestamp() matches what naive mock.now() returns:
_FIXED_NOW_NAIVE = datetime(2025, 12, 16, 12, 0, 0)
_FIXED_NOW_MS = int(_FIXED_NOW_NAIVE.timestamp() * 1000)
```

### Segment priority: set expiry far to avoid EXPIRING_SOON firing first

In `UserSegmenter.segment_rules`: EXPIRING_SOON is checked before INACTIVE_TRIAL.
Set `expiry_time = _FIXED_NOW_MS + 7 * 24 * 3600 * 1000` to keep key outside EXPIRING_SOON window.

### TelegramRetryAfter constructor

All aiogram exceptions require `method=MagicMock()` as first argument:
```python
TelegramRetryAfter(method=MagicMock(), message="...", retry_after=0)  # retry_after=0 for fast tests
```

### pool.acquire() mock for KeyExpiryFunnel

```python
conn = AsyncMock(); conn.execute = AsyncMock()
cm = AsyncMock(); cm.__aenter__ = AsyncMock(return_value=conn); cm.__aexit__ = AsyncMock()
pool = MagicMock(); pool.acquire = MagicMock(return_value=cm)  # NOT AsyncMock
```

## Registration Flow Tests (Stage 11 — 55 tests, all passing)

| File | Tests | Components |
|------|-------|-----------|
| `tests/middlewares/test_registration_users_flow.py` | 15 | RegistrationUsersMiddleware full flow |
| `tests/registration/test_gift_registration.py` | 11 | GiftRegistration can_handle/register |
| `tests/handlers/test_start_registration_flow.py` | 9 | send_massage_registration + send_massage_user_start |
| `tests/scenarios/test_create_first_key_flow.py` | 20 | CreateFerstKeyScenario get_data/start/errors |

### Critical: ServiceDataModel mock must NOT use spec=

`AsyncMock(spec=ServiceDataModel)` does NOT auto-create `.users`, `.gifts` etc. attributes.
Always build it manually:
```python
svc = AsyncMock()
svc.users = AsyncMock()
svc.users.get_data = AsyncMock(return_value=None)
```

### Critical: DB fallback in RegistrationUsersMiddleware

Middleware queries DB before token parsing. If mock service_model returns truthy user,
the middleware exits with `registered_user` before reaching token/factory logic.
For tests that need to reach token parsing: ensure `service_model.users.get_data` returns `None`.

### Patching GiftActivationScenario in handler tests

Use `patch("handlers.start.GiftActivationScenario", return_value=mock_scenario)` —
NOT manual attribute replacement on module. The `with MagicMock() as ...` pattern does not work.

### check_event_message() returns truthy object, not bool

`middleware.check_event_message(event)` returns `event.message or event.edited_message` (a MagicMock).
Use `assert middleware.check_event_message(event)` — NOT `assert ... is True`.

## Payment Module Tests (Stage 12 — 65 tests, all passing)

| File | Tests | Components |
|------|-------|-----------|
| `tests/payments/test_pay_config.py` | 24 | YooKassService (all 6 methods) |
| `tests/payments/test_webhook.py` | 18 | HandlersPayment + WebhookService |
| `tests/dialogs/getters/payment/test_form_pay_getter.py` | 13 | FormPaymentGetter |
| `tests/dialogs/keyboards/payment/test_form_pay_keyboard.py` | 10 | PaymentFormKeyboard |

### Critical: pyments_webhook.py circular import

`payments/pyments_webhook.py` imports `services.conteiner.app` at module level.
This creates a circular import chain when collected by pytest.
**Fix:** Stub the module in `sys.modules` before import:
```python
import sys
from unittest.mock import AsyncMock, MagicMock
_container_stub = MagicMock()
_container_stub.get_container = AsyncMock()
sys.modules.setdefault("services.conteiner.app", _container_stub)
from payments.pyments_webhook import HandlersPayment, WebhookService
```

### AsyncMock(spec=ConcreteClass) makes methods MagicMock, not AsyncMock

When mocking a class with `AsyncMock(spec=HandlersPayment)`, the methods on the mock
become `MagicMock`, not `AsyncMock` — so `assert_awaited_once_with` raises AttributeError.
**Fix:** Use `AsyncMock()` without spec when you need to assert await calls on methods.

### asyncio.to_thread positional args indexing

`to_thread(fn, arg1, arg2, arg3)` — args are positional:
- `call_args[0][0]` = fn
- `call_args[0][1]` = arg1
- `call_args[0][2]` = arg2
For `handle_payment_waiting`: `to_thread(Payment.capture, payment.id, amount_dict, idempotence_key)`.

### aiogram-dialog Column widget children

`Column.widgets` does NOT exist. Children are stored in `Column.buttons`.
```python
widget = keyboard.build()
assert len(widget.buttons) == 4
```

### FormPaymentGetter._get_payment_data empty dict fallback

`self._data = dialog_manager.dialog_data or dialog_manager.start_data`
Empty dict `{}` is falsy — falls back to `start_data`.
For "missing amount" test: set BOTH `dialog_data = {}` AND `start_data = {}`.
