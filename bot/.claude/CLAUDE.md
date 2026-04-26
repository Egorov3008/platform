# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Telegram bot (aiogram 3 + aiogram-dialog) for managing VPN subscriptions via the 3x-ui panel. Handles user registration, VPN key lifecycle, payments (YooKassa), gift links, referral system, tariffs, and admin functions. Written in Python 3.11, fully async.

## Commands

```bash
# Run the bot
python main.py

# Lint
make lint              # ruff check
make formatting        # ruff check --fix + ruff format

# Tests
pytest                 # all tests (asyncio_mode=auto, testpaths=tests)
pytest tests/models/   # test a specific module
pytest -k test_name    # run a single test by name

# Dead code detection
vulture . --min-confidence 100

# Type checking
mypy .
```

**See:** [docs/TESTS_MODULE.md](docs/TESTS_MODULE.md) — Complete testing guide (fixtures, patterns, structure)

## Architecture Overview

### Startup Flow

1. `setup_logging()` → 2. `on_startup()` (DI container, cache, background tasks) → 3. `setup_middlewares()` → 4. Router inclusion + polling

See [docs/modules.md](docs/modules.md) for detailed architecture.

### Middleware Stack (order matters)

**This order is critical:**

```
DatabaseMiddleware 
  → CacheMiddleware 
    → XUIMiddleware 
      → RegistrationUsersMiddleware 
        → LoggingMiddleware 
          → DialogExceptionHandlerMiddleware
```

Each middleware injects services into `data` dict: `data["session"]`, `data["cache"]`, `data["xui_session"]`, `data["registration_result"]`.

### Dependency Injection (punq)

Container created once via `services/conteiner/app.py:get_container()`. Services registered in `services/conteiner/registrate/`:
- `core/` — CoreService, Cache, Users, Keys, Gift, Tariff, Payment
- `getters/` — Dialog data getters
- `scenario/` — Business scenarios

Pattern: `container.register(Cls, factory=build_fn, scope=punq.Scope.singleton)`

### Data Access

Two-tier architecture: `CacheService` (in-memory with TTL) → `DataService` (asyncpg repositories) → `BaseRepository[T]` (generic CRUD).

Entry point: `ServiceDataModel` (wraps both tiers). Entities: `.users`, `.keys`, `.servers`, `.tariffs`, `.gifts`, `.inbounds`, `.payments`, `.stocks`.

**See:** [docs/database.md](docs/database.md), [docs/MODELS_MODULE.md](docs/MODELS_MODULE.md)

### Dialog System

Component-based factory pattern: `MessageBuilder` + `KeyboardBuilder` + `DataGetter` → `WindowFactory` → `Window`.

**See:** [docs/DIALOGS_MODULE.md](docs/DIALOGS_MODULE.md), [docs/GETTERS_MODULE.md](docs/GETTERS_MODULE.md)

### Handlers & States

Request routing in `handlers/` (start, admin, instructions, keys). FSM states in `states/` (MainMenu, Register, GiftStates, KeysInit, PaymentState, etc.).

**See:** [docs/STATES_MODULE.md](docs/STATES_MODULE.md)

### Key Business Services

- **keys/** — CreateKey, KeyRenewal, KeyUpdater, ExpiryCalculator, FormationKey
- **payment/** — PaymentProcessor, PaymentRouter
- **user/** — SaturationUser, TrialService, DeleteUser, CheckedUser
- **gift/** — GiftLinkProvider, TokenGen, CheckerGiftLink
- **segmentation/** — UserSegmenter, SegmentationManager

**See:** [docs/services.md](docs/services.md), [docs/PAYMENTS_MODULE.md](docs/PAYMENTS_MODULE.md), [docs/REGISTRATION_MODULE.md](docs/REGISTRATION_MODULE.md)

### External Integrations

- **3x-ui panel** — `client.py:XUISession` wraps `py3xui.AsyncApi`
- **YooKassa** — Webhook server in `payments/payments_webhook.py`
- **Database** — PostgreSQL via asyncpg pool

### Background Tasks

`BackgroundTaskManager` in `tasks.py`: cache sync (every 3h), notification funnels (every 1h), webhook server.

### Registration Flow

`RegistrationUsersMiddleware` → `RegistrationFactory` (GiftRegistration, ReferralRegistration) → result in `data["registration_result"]`.

## Configuration

All config via `.env` (loaded in `config.py`): Bot tokens, DB credentials, 3x-ui panel, YooKassa, webhook settings, tariff/pricing, referral percentages.

## Logging

`logger.py` provides `StructuredLogger` with sensitive data masking. Files: `logs/application.log` (INFO, 14d), `logs_error/errors.log` (ERROR, 28d), daily rotation with ZIP.

## Code Conventions

- **Language:** Project comments and messages in Russian
- **Async:** All database operations are async (asyncpg)
- **Design:** Protocol-based interfaces (`typing.Protocol`)
- **Generics:** Heavy use of `Generic[T]` and `TypeVar` in data layers
- **Note:** DI container package named `conteiner` (intentional legacy name — do not rename)

## Cache Access Rules

**CRITICAL:** Cache access strictly controlled via `CacheService` abstraction.

### ❌ FORBIDDEN

- Direct use of `ModelCache[T]` methods or instantiation
- `model_cache.get("key")`
- `ModelCache[User](storage, "users")`
- Accessing `ModelCache` from outside `CacheService`

### ✅ REQUIRED

All cache operations through `CacheService` attributes:
- `cache_service.users.get("user_id")`
- `cache_service.keys.set("key_id", key_obj)`
- `cache_service.servers.all()`
- `cache_service.gifts.delete("gift_id")`

### ⚠️ RARE EXCEPTION

`CacheService.storage` only in critical edge cases:
- Must document with explanatory comment
- Use only when `CacheService` API insufficient
- Examples: bulk operations, namespace purging

**Rationale:** Single entry point ensures consistent logging, monitoring, and future refactoring.

## Cache Key System (CacheKeyManager)

**CRITICAL:** Every model must use its correct identifier in the cache key generation via `CacheKeyManager`.

### Identifier Rules by Model

Each entity uses a **specific field** as its cache key identifier. **NEVER** use `id` generically:

| Model | Identifier Field | Key Pattern | Example |
|-------|------------------|-------------|---------|
| `User` | `tg_id` | `user_{tg_id}` | `cache_service.users.set(keys.user(123456), user)` |
| `Key` | **`email`** ⚠️ | `key_{email}` | `cache_service.keys.set(keys.key("user@ex.com"), key)` |
| `Server` | `id` | `server_{id}` | `cache_service.servers.set(keys.server(1), server)` |
| `Tariff` | `id` | `tariff_{id}` | `cache_service.tariffs.set(keys.tariff(10), tariff)` |
| `GiftLink` | `id` | `gift_{id}` | `cache_service.gifts.set(keys.gift(42), gift)` |
| `Inbound` | **(server_id, inbound_id)** ⚠️ | `inbound_{server_id}_{inbound_id}` | `cache_service.inbounds.set(keys.inbound(1, 5), inbound)` |
| `PaymentModel` | **`payment_id`** ⚠️ | `payment_{payment_id}` | `cache_service.payments.set(keys.payment("yoo_12345"), payment)` |
| `Stock` | `tg_id` | `stock_{tg_id}` | `cache_service.stocks.set(keys.stock(123456), stock)` |

### Common Mistakes ❌

```python
# WRONG: Key doesn't have .id attribute
cache_service.keys.set(keys.key(key_obj.id), key_obj)  # AttributeError!

# WRONG: Inbound requires TWO parameters, not one
cache_service.inbounds.set(keys.inbound(inbound_obj.id), inbound_obj)  # Wrong signature!

# WRONG: PaymentModel uses payment_id, not id
cache_service.payments.set(keys.payment(payment.id), payment)  # Uses wrong field!
```

### Correct Usage ✅

```python
# Load from cache with correct identifier
key = await cache_service.keys.get(keys.key("user@example.com"))  # Use email!

# Save to cache
await cache_service.keys.set(keys.key(key.email), key)

# Delete from cache
await cache_service.inbounds.delete(keys.inbound(inbound.server_id, inbound.inbound_id))

# Update in cache
await cache_service.payments.set(keys.payment(payment.payment_id), payment)
```

### Key Points

- **`CacheKeyManager`** in `services/cache/key_manager.py` is the single source of truth for all cache keys
- **`LoadingService`** uses these identifiers to load data on startup
- **`BaseData[T]`** uses `_extract_identifier()` to get the correct field for each model
- When adding a new model: update both `CacheKeyManager` and `BaseData._extract_identifier()`
- **Tests:** Run `pytest tests/services/cache/` to verify key generation

**Rationale:** Unified cache key system prevents data collisions, enables consistent lookups, and simplifies migration/refactoring.
