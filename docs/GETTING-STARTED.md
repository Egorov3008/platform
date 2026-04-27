<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks you through setting up the VPN Platform locally from scratch.

## Prerequisites

All three components require **Python 3.11+** (backend and bot use `python:3.11-slim`; web uses `python:3.12-slim`). You also need:

- **Docker and Docker Compose** — for the recommended full-stack startup
- **PostgreSQL 16** — provided via Docker; needed separately only for manual setup
- **pip** — to install Python dependencies per component
- A running **3x-UI panel** (external dependency) with API access
- A **YooKassa** merchant account for payment processing
- A **Telegram Bot token** from [@BotFather](https://t.me/BotFather)

## Installation Steps

### Option A: Docker Compose (recommended)

1. Clone the repository:

```bash
git clone <repository-url>
cd vpn-platform
```

2. Create `.env` files for each component from the provided examples:

```bash
cp backend/.env.example backend/.env
cp web/.env.example web/.env
```

3. Fill in the required values in each `.env` file. See [CONFIGURATION.md](CONFIGURATION.md) for the full variable reference.

4. Start all services:

```bash
docker-compose up -d
```

Docker Compose starts PostgreSQL first (with a health check), then backend (port 8000), bot, and web (port 8001) in dependency order.

### Option B: Manual per-component setup

1. Clone the repository:

```bash
git clone <repository-url>
cd vpn-platform
```

2. Install dependencies for each component:

```bash
# Backend
cd backend && pip install -r requirements.txt && cd ..

# Bot
cd bot && pip install -r requirements.txt && cd ..

# Web
cd web && pip install -r requirements.txt && cd ..
```

3. Copy and fill in the `.env` files:

```bash
cp backend/.env.example backend/.env
cp web/.env.example web/.env
# Bot has no .env.example — create bot/.env manually (see CONFIGURATION.md)
```

4. Apply web database migrations:

```bash
psql "$DATABASE_URL" -f web/migrations/001_web_auth.sql
psql "$DATABASE_URL" -f web/migrations/002_login_codes.sql
```

## First Run

After completing installation, start each component in separate terminals:

```bash
# Backend (port 8000)
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Web (port 8001)
cd web && uvicorn app.main:app --port 8001 --reload
```

Verify the backend is healthy:

```bash
curl http://localhost:8000/health
```

A successful response confirms PostgreSQL is reachable and the cache has loaded.

## Common Setup Issues

**Missing `BOT_SECRET_KEY` or mismatched secrets**
The bot and web components authenticate to the backend using `X-Bot-Secret: <BOT_SECRET_KEY>`. All three `.env` files must contain the same value for this key. A mismatch causes 401/403 errors on every API call.

**`DATABASE_URL` not set or wrong credentials**
Backend and web each connect to PostgreSQL via `asyncpg`. The default Docker Compose credentials are `vpn_user` / `changeme` on `localhost:5432/vpn_db`. If you run PostgreSQL outside Docker, update `DATABASE_URL` in both `backend/.env` and `web/.env`.

**3x-UI panel unreachable**
The backend requires a live 3x-UI panel (`API_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` in `backend/.env`). Key creation and renewal operations return 502 if the panel is down. Confirm the panel URL is reachable from the backend host before starting.

**Web auth tables missing**
If the web service starts but login fails immediately, the auth tables have not been created. Run the migrations in `web/migrations/` against your PostgreSQL database (see Option B step 4 above).

**Wrong Python version**
The backend and bot Dockerfiles pin `python:3.11-slim`; the web Dockerfile pins `python:3.12-slim`. Running with an older Python version (e.g., 3.9 or 3.10) will cause import errors due to newer type annotation syntax.

**Bot `network_mode: host` on non-Linux hosts**
In `docker-compose.yml`, the bot container uses `network_mode: host`. This mode is only supported on Linux. On macOS or Windows Docker Desktop, remove `network_mode: host` and add an explicit port mapping instead.

## Next Steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — component overview, data flow, and service boundaries
- [CONFIGURATION.md](CONFIGURATION.md) — full environment variable reference for all three components
- See `backend/CLAUDE.md` for backend API endpoint details and testing patterns
- See `web/CLAUDE.md` for web layer architecture and `WebBackendClient` usage
