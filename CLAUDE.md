# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Full Stack
```bash
docker-compose up -d
```

### Component Development
```bash
# Backend (port 8000)
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Web (port 8001)
cd web && uvicorn app.main:app --port 8001 --reload
```

### Tests
```bash
# Backend
cd backend && pytest
cd backend && pytest tests/api/test_keys.py
cd backend && pytest tests/api/test_keys.py::test_list_keys

# Bot
cd bot && pytest
cd bot && pytest tests/models/
cd bot && pytest -k test_name
cd bot && make test          # via Makefile

# Web (unit)
cd web && pytest

# Web (E2E, requires browser)
cd web && npx playwright test
cd web && npx playwright test --grep "auth"
```

### Lint
```bash
# Bot only (has Makefile)
cd bot && make lint
cd bot && make formatting
```

## Monorepo Architecture

| Component | Path | Role | Dev Port |
|---|---|---|---|
| FastAPI Backend | `backend/` | Source of truth: business logic, 3x-UI, YooKassa, cache | 8000 |
| Telegram Bot | `bot/` | UI layer: dialogs, handlers, user notifications | — |
| Web Interface | `web/` | SPA + thin FastAPI proxy over backend API | 8001 |

**Contract:** Bot and web **never access the database directly** — only through the backend API. All business logic (keys, payments, tariffs), 3x-UI and YooKassa integrations live exclusively in `backend/`.

## Authentication Between Services

| Client | Header | Description |
|---|---|---|
| Bot → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret |
| Web → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret (service-to-service) |
| User → Web | JWT in HttpOnly cookie | `access_token` + `refresh_token` |
| Admin → Backend | `X-API-Key: <ADMIN_API_KEY>` | Admin operations |

## Cache & Identifiers (Critical)

`CacheService` is an in-memory TTL cache used in both **backend** and **bot**. Identifiers must match across services because the cache key system is shared:

| Entity | Identifier | Example Key |
|---|---|---|
| `User` | `tg_id` | `user_123456` |
| `Key` | **`email`** (not `id`!) | `key_user@example.com` |
| `Inbound` | `(server_id, inbound_id)` | `inbound_1_5` |
| `PaymentModel` | **`payment_id`** (not `id`!) | `payment_yoo_12345` |

## Bot Architecture (aiogram 3)

The bot uses a **middleware stack** where order matters. Each middleware injects services into the aiogram `data` dict:

```
DependencyInjectionMiddleware  → data["container"]
  → DatabaseMiddleware           → data["session"]
    → CacheMiddleware            → data["cache"]
      → XUIMiddleware            → data["xui_session"]
        → RegistrationUsersMiddleware → data["registration_result"]
          → AdminSearchMiddleware
            → SubscriptionMiddleware
              → LoggingMiddleware
                → DialogExceptionHandlerMiddleware
```

**DI container:** `punq` singleton container built in `services/conteiner/app.py`. Package is intentionally named `conteiner` (legacy spelling — do not rename).

**Dialogs:** Component-based factory pattern (`MessageBuilder` + `KeyboardBuilder` + `DataGetter` → `WindowFactory`).

**Background tasks:** `BackgroundTaskManager` in `tasks.py` runs cache sync, notification funnels, and webhook server.

## Backend Request Flow

```
Bot/Web API Client
    ↓
FastAPI Router (/api/v1/*)
    ├─ verify_bot_secret (X-Bot-Secret header check)
    └─ Call service/factory functions
    ↓
Service Classes (KeyCreation, PaymentProcessor, KeyRenewal)
    ├─ 3x-UI integration (py3xui client)
    ├─ YooKassa payment processing
    ├─ Cache invalidation
    └─ Database updates
    ↓
PostgreSQL + 3x-UI Panel
```

**Core service factories:**
- `build_key_services(pool, service_data, cache, data_service)` → returns `(create_key, key_renewal, xui)`
- `build_payment_router(pool, service_data, cache, data_service)` → returns `PaymentRouter` (calls `build_key_services` internally)

**Telegram notifications:** Backend sends user notifications via `backend/bot_project.py`, a lightweight httpx wrapper around the Bot API. It does not depend on aiogram.

## Per-Component Deep Dives

- `backend/CLAUDE.md` — Endpoint details, service factories, 3x-UI/YooKassa flows, testing patterns with AsyncMock
- `web/CLAUDE.md` — Auth flow (JWT + Telegram Widget), WebBackendClient, E2E test markers, local auth DB schema
- `bot/.claude/CLAUDE.md` — Dialog system, getters, cache key rules, registration flow, dead-code detection (`vulture`)

## Environment Variables

Each component requires its own `.env`. Critical cross-cutting variables:

- `DATABASE_URL` — asyncpg DSN (backend uses full schema; web uses only auth tables)
- `BOT_SECRET_KEY` — shared secret for Bot→Backend and Web→Backend
- `XUI_API_URL` / `XUI_LOGIN` / `XUI_PASSWORD` — 3x-UI panel credentials
- `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` — payment processing
- `TELEGRAM_BOT_TOKEN` — for sending user notifications from backend (`backend/bot_project.py`)
- `WEBHOOK_BASE_URL` — public URL for YooKassa callbacks
- `ADMIN_TG_IDS` — JSON array of admin Telegram IDs
