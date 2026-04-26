# VPN Web Backend — Project Context

## Project Overview

**VPN Web Backend** is a FastAPI-based backend service for managing VPN subscriptions through a web interface. It provides a complete solution for user authentication, VPN key management, tariff plans, payment processing via YooKassa, and administrative analytics with dashboard metrics (MRR, user funnel, conversion rates, key expiry tracking).

### Architecture

The project follows a layered architecture:

```
app/
├── api/          — FastAPI routers (endpoints)
├── services/     — Business logic layer
├── repositories/ — Data access layer (raw SQL via asyncpg)
├── schemas/      — Pydantic models for request/response validation
└── core/         — Infrastructure (config, DB, security, dependencies, xui client)
```

### Key Integrations

- **PostgreSQL** — Primary data store (asyncpg connection pool)
- **3x-UI** — VPN panel for managing client keys (via `py3xui`)
- **YooKassa** — Payment gateway for processing subscriptions
- **Telegram Bot API** — Magic-link authentication via Telegram messages

### Tech Stack

- **Python 3.12**, **FastAPI 0.115**, **Uvicorn**
- **asyncpg** — Async PostgreSQL driver
- **Pydantic v2** — Data validation
- **python-jose** + **passlib[bcrypt]** — JWT tokens and password hashing
- **pytest** + **pytest-asyncio** — Testing
- **Docker** — Containerization

---

## Building and Running

### Local Development

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your values

# 2. Run database migrations
psql "$DATABASE_URL" -f migrations/001_web_auth.sql

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker-compose up -d
```

### API Documentation

Interactive Swagger UI: `http://localhost:8000/docs`

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py
pytest tests/test_admin.py
pytest tests/test_keys.py
pytest tests/test_tariffs.py
pytest tests/test_payments.py
pytest tests/test_security.py
```

Tests use `httpx.AsyncClient` with mocked database connections (via dependency overrides) for most test files, except `test_auth.py` which works with a real database from docker-compose.

---

## API Endpoints

| Prefix | Module | Auth Required | Description |
|---|---|---|---|
| `/api/v1/auth/*` | `auth.py` | No (except refresh) | Registration, login, magic-link, token refresh |
| `/api/v1/keys/*` | `keys.py` | Yes | CRUD for user's VPN keys |
| `/api/v1/tariffs/*` | `tariffs.py` | No | Public tariff listing |
| `/api/v1/payments/*` | `payments.py` | Yes (create) | Payment creation and YooKassa webhook |
| `/api/v1/admin/*` | `admin.py` | Admin only | Dashboard stats, user/key management |
| `/health` | `main.py` | No | Health check |

---

## Configuration

All settings are loaded from environment variables via `pydantic-settings`. See `.env.example` for the full list:

- **Database**: `DATABASE_URL`
- **JWT**: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `ADMIN_TG_IDS`
- **Payments**: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `WEBHOOK_BASE_URL`, `DISABLE_WEBHOOK_IP_CHECK`
- **3x-UI**: `XUI_API_URL`, `XUI_LOGIN`, `XUI_PASSWORD`, `XUI_INBOUND_ID`
- **Magic-link**: `MAGIC_TOKEN_TTL_MINUTES`

---

## Database Schema

Tables managed by SQL migrations in `migrations/`:

| Table | Purpose |
|---|---|
| `web_users` | Web user accounts (email/password or Telegram-linked) |
| `users` | Telegram users (from bot's schema) |
| `keys` | VPN key records linked to users and tariffs |
| `tariff` | Tariff plans (name, price, traffic limits, IP limits) |
| `payments` | Payment records with YooKassa |
| `magic_tokens` | One-time tokens for Telegram magic-link auth |

---

## Development Conventions

- **Russian docstrings** — All module and class docstrings are written in Russian
- **Layered separation** — API routers call service functions, which use repositories for DB access
- **Dependency injection** — FastAPI `Depends()` for DB connections and auth
- **Async-first** — All DB operations use asyncpg asynchronously
- **Mock-based testing** — Most tests override `get_conn` dependency with `AsyncMock` to avoid real DB
- **No repository tests** — Repositories are thin SQL wrappers; testing focuses on API/service layer
