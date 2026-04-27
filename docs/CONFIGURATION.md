<!-- generated-by: gsd-doc-writer -->
# Configuration

This document describes all environment variables and configuration settings for the VPN platform. The platform consists of three components — **backend**, **bot**, and **web** — each with its own `.env` file. A root-level `.env.example` provides a reference for the shared PostgreSQL credentials.

---

## Root-Level: Docker Compose Variables

These variables are consumed by `docker-compose.yml` to configure the PostgreSQL container. Copy `.env.example` to `.env` at the project root before running `docker-compose up`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_NAME` | Optional | `vpn_db` | PostgreSQL database name |
| `DB_USER` | Optional | `vpn_user` | PostgreSQL username |
| `DB_PASSWORD` | **Required** | `changeme` | PostgreSQL password (change before deploying) |

---

## Backend (`backend/.env`)

The backend is the source of truth for all business logic. Copy `backend/.env.example` to `backend/.env`.

### Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **Required** | — | asyncpg DSN, e.g. `postgresql://vpn_user:changeme@localhost:5432/vpn_db` |

### Security

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_SECRET_KEY` | **Required** | `changeme` | Shared secret used by bot and web to authenticate requests via `X-Bot-Secret` header |
| `ADMIN_API_KEY` | **Required** | `changeme` | API key for admin endpoints, passed via `X-API-Key` header |

Both keys default to `changeme` but should be replaced with strong random secrets before deployment.

### 3x-UI Panel

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_URL` | **Required** | — | Base URL of the 3x-UI panel, e.g. `http://your-panel:2095` |
| `ADMIN_USERNAME` | **Required** | — | 3x-UI admin login |
| `ADMIN_PASSWORD` | **Required** | — | 3x-UI admin password |

### YooKassa Payments

| Variable | Required | Default | Description |
|---|---|---|---|
| `YOOKASSA_SHOP_ID` | **Required** | — | YooKassa shop identifier |
| `YOOKASSA_SECRET_KEY` | **Required** | — | YooKassa secret key (use `test_` prefix for testing) |
| `DISABLE_WEBHOOK_IP_CHECK` | Optional | `false` | Set to `true` to skip YooKassa IP whitelist verification (development only) |

### Telegram

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | **Required** | — | Telegram bot token (used for sending user notifications) |
| `BOT_NAME` | Optional | `VPNBot` | Telegram bot username |
| `SUPPORT_CHAT_URL` | Optional | — | URL of the support chat, e.g. `https://t.me/support_chat` |
| `URL_BOT` | Optional | — | Public URL of the bot, e.g. `https://t.me/MyVPNBot` |

### Bot Behaviour

| Variable | Required | Default | Description |
|---|---|---|---|
| `ADMIN_ID` | Optional | `[0]` | JSON array of admin Telegram IDs, e.g. `[123456789]` |
| `AVAILABLE_RATES` | Optional | `[9, 8, 7]` | JSON array of tariff IDs shown to users |
| `AVAILABLE_CONNECTIONS` | Optional | `[11, 12]` | JSON array of allowed inbound connection IDs |
| `DEFAULT_PRICING_PLAN` | Optional | `10` | Default tariff ID for new users |
| `TRIAL_TIME` | Optional | `30` | Trial period duration in days |
| `DISCOUNTS` | Optional | `3` | Volume discount percentage for multi-month subscriptions |

### Monitoring

| Variable | Required | Default | Description |
|---|---|---|---|
| `METRICS_PORT` | Optional | `9101` | Port on which Prometheus metrics are exposed |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Webhook

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEBHOOK_HOST` | Optional | `0.0.0.0` | Webhook server bind host |
| `WEBHOOK_PORT` | Optional | `8000` | Webhook server bind port |
| `WEBHOOK_PATH` | Optional | `/api/v1/payments/webhook` | Path where YooKassa posts payment webhooks |

---

## Bot (`bot/.env`)

The bot is a pure UI layer. It reads the same `.env` format but uses a different set of variables. The bot validates at startup that `BOT_TOKEN`, `ADMIN_ID`, `DATABASE_URL`, `AVAILABLE_CONNECTIONS`, `AVAILABLE_RATES`, and `PAYMENT_INFO` are all present; missing any of these causes the bot to exit immediately.

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | **Required** | — | Telegram bot token |
| `DATABASE_URL` | **Required** | — | PostgreSQL DSN |
| `ADMIN_ID` | **Required** | — | JSON array of admin Telegram IDs |
| `AVAILABLE_CONNECTIONS` | **Required** | — | JSON array of allowed inbound connection IDs |
| `AVAILABLE_RATES` | **Required** | — | JSON array of tariff IDs |
| `PAYMENT_INFO` | **Required** | `{}` | JSON dict with payment provider info |
| `BACKEND_URL` | Optional | `http://localhost:8000` | Backend API base URL |
| `BOT_SECRET_KEY` | Optional | `""` | Shared secret for backend requests (must match backend value) |
| `YOOKASSA_SECRET_KEY` | Optional | — | YooKassa secret key |
| `YOOKASSA_SHOP_ID` | Optional | — | YooKassa shop ID |
| `BOT_NAME` | Optional | — | Bot display name |
| `SUPPORT_CHAT_URL` | Optional | — | Support chat URL |
| `URL_BOT` | Optional | — | Public bot URL |
| `DEFAULT_PRICING_PLAN` | Optional | — | Default tariff ID |
| `METRICS_PORT` | Optional | `9101` | Prometheus metrics port |
| `WEBHOOK_HOST` | Optional | `0.0.0.0` | Webhook bind host |
| `WEBHOOK_PORT` | Optional | `5001` | Webhook bind port |
| `WEBHOOK_PATH` | Optional | — | Webhook path |
| `DISABLE_WEBHOOK_IP_CHECK` | Optional | `false` | Skip YooKassa IP check |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity |

---

## Web (`web/.env`)

The web layer is a stateless API proxy and auth layer. It stores only authentication tables locally. Copy `web/.env.example` to `web/.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **Required** | — | PostgreSQL DSN for auth tables only (`login_codes`, `web_users`, `magic_tokens`) |
| `SECRET_KEY` | **Required** | — | JWT signing key |
| `TELEGRAM_BOT_TOKEN` | **Required** | — | Telegram bot token (for bot integration) |
| `YOOKASSA_SHOP_ID` | **Required** | — | YooKassa shop ID |
| `YOOKASSA_SECRET_KEY` | **Required** | — | YooKassa secret key |
| `XUI_API_URL` | **Required** | — | 3x-UI panel API URL |
| `XUI_LOGIN` | **Required** | — | 3x-UI admin login |
| `XUI_PASSWORD` | **Required** | — | 3x-UI admin password |
| `WEBHOOK_BASE_URL` | **Required** | — | Public base URL for YooKassa webhook callbacks |
| `BACKEND_URL` | Optional | `http://localhost:8000` | Backend API base URL (use `http://backend:8000` in Docker) |
| `BOT_SECRET_KEY` | Optional | `""` | Shared secret for backend requests (`X-Bot-Secret` header; must match backend value) |
| `ALGORITHM` | Optional | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `30` | JWT access token TTL in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Optional | `30` | JWT refresh token TTL in days |
| `TELEGRAM_BOT_USERNAME` | Optional | `""` | Telegram bot username (without `@`) |
| `XUI_SUBSCRIPTION_URL` | Optional | `""` | 3x-UI subscription link base URL |
| `XUI_INBOUND_ID` | Optional | `1` | Default inbound ID for new VPN keys |
| `ADMIN_TG_IDS` | Optional | `[]` | JSON array of admin Telegram IDs |
| `LOGIN_CODE_TTL_HOURS` | Optional | `24` | Lifetime of login codes in hours |
| `CSRF_ENABLED` | Optional | `true` | Enable CSRF protection (set to `false` in tests/dev only) |
| `DEFAULT_TRIAL_TARIFF_ID` | Optional | `10` | Tariff ID used for free trial keys |
| `DEFAULT_SERVER_ID` | Optional | `2` | Default server ID assigned to new users |
| `REFERRAL_BONUS_PERCENT` | Optional | `0.10` | Referral bonus fraction of payment amount |
| `VOLUME_DISCOUNT_PERCENT` | Optional | `0.03` | Discount fraction for multi-month subscriptions |
| `AVAILABLE_RATES` | Optional | `[]` | Tariff IDs visible to regular users (empty = all tariffs) |
| `DISABLE_WEBHOOK_IP_CHECK` | Optional | `false` | Skip YooKassa IP whitelist check |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity |
| `LOG_FILE` | Optional | `""` | Log output file path (default: stdout) |
| `LOG_FORMAT` | Optional | `detailed` | Log format: `detailed`, `simple`, or `json` |

---

## Shared Secrets

Two secrets must be set to the **same value** across components for inter-service authentication to work:

| Secret | Backend | Bot | Web | Purpose |
|---|---|---|---|---|
| `BOT_SECRET_KEY` | `backend/.env` | `bot/.env` | `web/.env` | Authenticates bot and web requests to backend via `X-Bot-Secret` header |

The `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY` values should also be identical across all components that interact with YooKassa.

---

## Per-Environment Overrides

There are no separate `.env.development` or `.env.production` files. Per-environment configuration is handled by:

1. **Docker Compose** — uses `./backend/.env`, `./bot/.env`, and `./web/.env` via `env_file` directives.
2. **Local development** — create `.env` files per component and run each service directly.
3. **`DISABLE_WEBHOOK_IP_CHECK`** — set to `true` in development to bypass YooKassa IP whitelisting.
4. **`CSRF_ENABLED`** — set to `false` in the web component during local testing.

<!-- VERIFY: Production deployment uses platform secret manager (e.g., Docker Swarm secrets or Kubernetes Secrets) rather than .env files -->
