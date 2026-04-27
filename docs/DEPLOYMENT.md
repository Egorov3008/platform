<!-- generated-by: gsd-doc-writer -->
# Deployment

This document describes how to deploy the VPN platform — a monorepo with three components: **backend** (FastAPI, port 8000), **bot** (Telegram aiogram), and **web** (FastAPI proxy, port 8001) — backed by a shared PostgreSQL database.

---

## Deployment Targets

The platform supports Docker Compose as the primary deployment method. Each component also has a standalone Dockerfile for independent container deployment.

| Target | Config File | Description |
|---|---|---|
| Full platform (Docker Compose) | `docker-compose.yml` | Runs all four services: postgres, backend, bot, web |
| Backend container | `backend/Dockerfile` | Python 3.11-slim, uvicorn on port 8000 |
| Bot container | `bot/Dockerfile` | Python 3.11-slim, runs `python main.py`, `network_mode: host` |
| Web container | `web/Dockerfile` | Python 3.12-slim, uvicorn on port 8000 (mapped to 8001) |
| Bot standalone | `bot/docker-compose.yml` | Bot service only, no database |
| Web standalone | `web/docker-compose.yml` | Web service only, no database |
| Monitoring stack | `bot/docker-compose.monitoring.yml` | Prometheus, Grafana, Loki, Promtail, Tempo, OpenTelemetry Collector |

---

## Build Pipeline

No CI/CD pipeline is detected in the repository. Deployment is performed manually.

### Full Platform Deployment

1. Provision a Linux server with Docker and Docker Compose installed.
2. Clone the repository and navigate to the project root:

```bash
git clone <repository-url>
cd vpn-platform
```

3. Configure environment files — see [Environment Setup](#environment-setup) below.
4. Build and start all services:

```bash
docker-compose up -d --build
```

5. Verify services are healthy:

```bash
docker-compose ps
curl http://localhost:8000/health   # backend
curl http://localhost:8001/health   # web
```

6. Apply web database migrations (first deploy only):

```bash
docker-compose exec web psql "$DATABASE_URL" -f migrations/001_web_auth.sql
docker-compose exec web psql "$DATABASE_URL" -f migrations/002_login_codes.sql
docker-compose exec web psql "$DATABASE_URL" -f migrations/003_stocks_per_user.sql
docker-compose exec web psql "$DATABASE_URL" -f migrations/004_referral_tables.sql
docker-compose exec web psql "$DATABASE_URL" -f migrations/005_add_referral_discount.sql
docker-compose exec web psql "$DATABASE_URL" -f migrations/006_add_servers_and_update_schema.sql
```

### Development Component Startup

Each component can be started independently without Docker:

```bash
# Backend (port 8000)
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Web (port 8001)
cd web && uvicorn app.main:app --port 8001 --reload
```

---

## Environment Setup

Each component requires its own `.env` file. A root `.env` file is also required for Docker Compose to configure the PostgreSQL container.

### Step 1: Root `.env` (PostgreSQL credentials for Docker Compose)

Copy `.env.example` to `.env` at the project root and set a strong database password:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `DB_NAME` | Optional | PostgreSQL database name (default: `vpn_db`) |
| `DB_USER` | Optional | PostgreSQL username (default: `vpn_user`) |
| `DB_PASSWORD` | **Required** | PostgreSQL password — change `changeme` before deploying |

### Step 2: Backend `backend/.env`

Copy `backend/.env.example` to `backend/.env`. Required variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Required** | asyncpg DSN, e.g. `postgresql://vpn_user:changeme@localhost:5432/vpn_db` |
| `BOT_SECRET_KEY` | **Required** | Shared secret used by bot and web to authenticate requests (`X-Bot-Secret` header) |
| `ADMIN_API_KEY` | **Required** | Secret for admin endpoint access (`X-API-Key` header) |
| `API_URL` | **Required** | 3x-UI panel base URL, e.g. `http://your-panel:2095` |
| `ADMIN_USERNAME` | **Required** | 3x-UI panel login |
| `ADMIN_PASSWORD` | **Required** | 3x-UI panel password |
| `YOOKASSA_SHOP_ID` | **Required** | YooKassa merchant shop ID |
| `YOOKASSA_SECRET_KEY` | **Required** | YooKassa secret key |
| `BOT_TOKEN` | **Required** | Telegram bot token (for sending user notifications) |
| `WEBHOOK_BASE_URL` | **Required** | <!-- VERIFY: public HTTPS URL where YooKassa POSTs payment webhooks, e.g. https://api.example.com --> |
| `ADMIN_ID` | **Required** | JSON array of admin Telegram IDs, e.g. `[123456789]` |
| `DISABLE_WEBHOOK_IP_CHECK` | Optional | Set `true` to skip YooKassa IP whitelist check (default: `false`) |
| `LOG_LEVEL` | Optional | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `METRICS_PORT` | Optional | Prometheus metrics scrape port (default: `9101`) |

### Step 3: Bot `bot/.env`

The bot reads its own `.env` file. Required variables (no `.env.example` in the bot directory — use `backend/.env.example` as reference for shared fields):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Required** | asyncpg DSN for the shared PostgreSQL database |
| `BOT_TOKEN` | **Required** | Telegram bot token |
| `ADMIN_ID` | **Required** | JSON array of admin Telegram IDs |
| `BOT_SECRET_KEY` | **Required** | Must match `BOT_SECRET_KEY` in `backend/.env` |
| `API_URL` | **Required** | 3x-UI panel base URL |
| `ADMIN_USERNAME` | **Required** | 3x-UI panel login |
| `ADMIN_PASSWORD` | **Required** | 3x-UI panel password |

### Step 4: Web `web/.env`

Copy `web/.env.example` to `web/.env`:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Required** | asyncpg DSN for the web auth tables only |
| `SECRET_KEY` | **Required** | JWT signing key |
| `BOT_SECRET_KEY` | **Required** | Must match `BOT_SECRET_KEY` in `backend/.env` |
| `BACKEND_URL` | **Required** | Backend API base URL — use `http://backend:8000` when running via Docker Compose |
| `CSRF_ENABLED` | Optional | Set `false` to disable CSRF checks for testing/dev (default: `true`) |
| `LOG_LEVEL` | Optional | Logging level (default: `INFO`) |

---

## Rollback Procedure

No automated rollback pipeline is configured. To roll back a deployment:

1. Identify the previous working image tag or git commit:

```bash
docker images | grep vpn-platform
git log --oneline -10
```

2. Check out the previous commit and rebuild:

```bash
git checkout <previous-commit-sha>
docker-compose up -d --build
```

3. Alternatively, redeploy from the previous Docker image tag if images are tagged and pushed to a registry:

```bash
# <!-- VERIFY: replace with your container registry image tags -->
docker-compose down
docker tag <registry>/vpn-backend:<previous-tag> vpn-platform-backend:latest
docker-compose up -d
```

4. If database schema changes were applied in the failed deploy, restore from a PostgreSQL backup before redeploying the old code:

```bash
# <!-- VERIFY: confirm backup location and restore procedure with your DBA or ops team -->
docker-compose exec postgres pg_restore -U vpn_user -d vpn_db /backups/vpn_db_<date>.dump
```

5. After rollback, force-refresh the backend in-memory cache:

```bash
curl -X POST http://localhost:8000/api/v1/admin/rebuild-cache \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

---

## Monitoring

The platform includes a full observability stack defined in `bot/docker-compose.monitoring.yml`.

### Starting the Monitoring Stack

```bash
cd bot
docker-compose -f docker-compose.monitoring.yml up -d
```

This starts:

| Service | Port | Description |
|---|---|---|
| Prometheus | `9092` | Metrics collection; scrapes bot metrics at `localhost:9101` |
| Grafana | `3001` | Dashboards; pre-provisioned from `bot/grafana-dashboard.json` |
| Loki | <!-- VERIFY: Loki default port from loki-config.yml --> | Log aggregation |
| Promtail | — | Log collector; reads `bot/logs/` and `bot/logs_error/` |
| Tempo | — | Distributed tracing |
| OpenTelemetry Collector | — | Collector receiving traces and forwarding to Tempo/Loki |

The default Grafana admin password is `admin` (set via `GF_SECURITY_ADMIN_PASSWORD`). <!-- VERIFY: change GF_SECURITY_ADMIN_PASSWORD before exposing Grafana publicly -->

### Metrics

The backend exposes Prometheus metrics via `prometheus-client` on port `9101` (configurable via `METRICS_PORT` in `backend/.env`).

### Alerting

Alert rules are defined in `bot/alerts.yml`. Key alerts:

| Alert | Condition | Severity |
|---|---|---|
| `HighErrorRate` | > 10 errors/min for 2 min | critical |
| `CriticalErrorsDetected` | Any critical error for 1 min | critical |
| `DatabaseErrors` | > 5 DB errors/min for 3 min | warning |
| `XuiApiErrors` | > 10 3x-UI API errors/min for 2 min | warning |
| `PaymentErrors` | > 3 payment errors/min for 2 min | critical |
| `BotDown` | Bot unreachable for 1 min | critical |
| `HighMemoryUsage` | > 500 MB RSS for 5 min | warning |

### Health Endpoints

Both the backend and web services expose health check endpoints:

```bash
GET http://localhost:8000/health      # backend: {"status": "ok"}
GET http://localhost:8000/readiness   # backend: DB connectivity check
GET http://localhost:8001/health      # web: {"status": "ok"}
```

These are used by Docker Compose `healthcheck` directives (`interval: 30s`, `timeout: 10s`, `retries: 3`).

---

## Systemd Service (Alternative to Docker)

A systemd unit file is provided for running the bot as a system service without Docker (`bot/bot.service`). To install it:

```bash
# Adjust User, Group, WorkingDirectory, and ExecStart paths as needed
sudo cp bot/bot.service /etc/systemd/system/bot_3xui_vpn.service
sudo systemctl daemon-reload
sudo systemctl enable bot_3xui_vpn
sudo systemctl start bot_3xui_vpn
```

The service is configured with:
- `Restart=on-failure` with 5 restart steps and 60s max delay
- `MemoryLimit=1G` / `MemoryHigh=800M` resource caps
- stdout/stderr forwarded to systemd journal (`journalctl -u bot_3xui_vpn`)
