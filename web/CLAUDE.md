# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run a single test file
pytest tests/test_auth.py

# Run a single test
pytest tests/test_auth.py::test_register

# Apply database migrations
psql "$DATABASE_URL" -f migrations/001_web_auth.sql
psql "$DATABASE_URL" -f migrations/002_login_codes.sql
```

## Architecture Overview

This is a **FastAPI async backend** for a VPN subscription service. The layered architecture flows: `api → services → repositories → asyncpg (raw SQL)`.

### Request Flow

1. **`app/api/`** — FastAPI routers receive requests, extract JWT claims via `Depends(get_current_user)`, call service functions
2. **`app/services/`** — Business logic; coordinates between repositories and external APIs (3x-UI, YooKassa, Telegram Bot API)
3. **`app/repositories/`** — Raw SQL via asyncpg; each repo class wraps a table

### Key Architectural Decisions

**Database**: asyncpg connection pool (`app/core/database.py`). Connections are injected per-request via `Depends(get_conn)`. No ORM — all queries are raw SQL strings.

**Auth**: JWT-based (python-jose). Access + refresh token pair stored in **HttpOnly cookies** (`access_token`, `refresh_token`). A non-HttpOnly `csrf_token` cookie enables CSRF double-submit validation (`X-CSRF-Token` header). Admin status is embedded in JWT as `is_admin: bool` from `ADMIN_TG_IDS`. Single login flow:
- Telegram bot generates an 8-char alphanumeric code (`login_codes` table, 24 h TTL, single-use) via `POST /api/v1/bot/auth/generate-code` (protected by `X-Bot-Secret` header)
- User submits code on the website → `POST /api/v1/auth/login` → cookies set

Bot is a separate repository; it calls this service's bot API.

**VPN key management**: Keys live in a 3x-UI panel (XRay/V2Ray). `app/core/xui.py` holds a lazy singleton `AsyncApi` client (py3xui). Keys are created in 3x-UI first, then saved to PostgreSQL.

**Payments**: YooKassa integration. `payment_type` field encodes the operation as `"web_new_key|{tg_id}:{tariff_id}"`. On webhook success, the service creates a VPN key automatically. Idempotency is enforced by checking `status == "succeeded"` before processing.

**Frontend**: Single-file SPA (`frontend/index.html`) with hash routing, served as StaticFiles. No framework.

### Two User Tables

There are **two separate user tables**:
- `users` — original Telegram bot users (identified by `tg_id`), managed by the Telegram bot (not this service)
- `web_users` — web interface users, created automatically on first login; linked to `users.tg_id`

VPN keys require a `tg_id` (linked Telegram account). Login always provides a `tg_id` via the code flow, so `web_users` are always linked.

### Admin Access

Admin is determined by `tg_id` membership in `ADMIN_TG_IDS` config list. The `is_admin` flag is embedded in JWT at login, so config changes require re-login. Admin endpoints are under `/api/v1/admin/` and use `Depends(require_admin)`.

### Logging

Structured logging via `app/core/logging.py`. Use `get_logger(__name__)` in every module. Configurable via `LOG_LEVEL`, `LOG_FILE`, `LOG_FORMAT` (detailed/simple/json) env vars.

### Background Tasks & Scheduler

Uses **APScheduler** (`app/background/scheduler.py`) to run periodic jobs during app lifetime:

**Jobs (defined in `add_jobs()`):**
- `sync_data_from_db` — runs every 3 hours, syncs cached data from PostgreSQL (placeholder for future Redis caching)
- `send_expiry_notifications` — runs hourly, finds VPN keys expiring within 24h and marks them; TODO: integrate with Telegram bot for actual notifications

**Lifecycle:**
- `init_scheduler()` — creates and starts AsyncIOScheduler at app startup (in `lifespan()`)
- `add_jobs(pool)` — registers periodic jobs, receives DB pool for async access
- `shutdown_scheduler()` — cleanly shuts down on app shutdown

Jobs are defined as `async def` and receive the asyncpg pool as an argument. All jobs log their progress via the logger.

## Testing Patterns

Tests mock the asyncpg connection via `app.core.dependencies.get_conn` override. The `mock_conn` fixture in `tests/conftest.py` returns `(mock_conn, mock_pool)`. Each test file creates its own `client` fixture with overridden dependencies.

```python
# Standard pattern for test setup
app.dependency_overrides[get_conn] = lambda: override_get_conn()
async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
    yield c
app.dependency_overrides.clear()
```

Tests are marked `@pytest.mark.asyncio` and use `AsyncMock` for DB calls. The 3x-UI client is also mocked in key-related tests.

## Environment Variables

Required in `.env` (see `.env.example`):
- `DATABASE_URL` — asyncpg DSN
- `SECRET_KEY` — JWT signing key
- `TELEGRAM_BOT_TOKEN` — for Telegram Bot API calls (notifications etc.)
- `TELEGRAM_BOT_USERNAME` — shown on the login page so users can find the bot
- `BOT_SECRET_KEY` — shared secret between this service and the bot (`X-Bot-Secret` header)
- `LOGIN_CODE_TTL_HOURS` — code expiry in hours (default: 24)
- `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` — payment processing
- `XUI_API_URL` / `XUI_LOGIN` / `XUI_PASSWORD` / `XUI_INBOUND_ID` — 3x-UI panel access
- `WEBHOOK_BASE_URL` — public URL for YooKassa webhook callbacks
- `ADMIN_TG_IDS` — JSON array of Telegram IDs with admin access
- `CSRF_ENABLED` — set to `false` to disable CSRF checks (tests/dev only)
- `DISABLE_WEBHOOK_IP_CHECK=true` — skip YooKassa IP verification in dev/testing
