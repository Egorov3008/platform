# Dev environment setup

This project runs a **production** stack on the server. The dev stack is completely separate: separate DB volume, separate bot token, separate YooKassa test account, and a separate public webhook URL (via ngrok).

## What you get

| Service | Prod | Dev |
|---|---|---|
| Postgres | port `5433`, volume `postgres_data` | port `5434`, volume `postgres_dev_data` |
| Backend | `backend` container (port 8000 internally) | `backend_dev` container, host port **8000** |
| Web | `web` container (port 8000 internally) | `web_dev` container, host port **8001** |
| Bot | `bot` container, polling | `bot_dev` container, polling |
| Nginx | prod ports `80/443` | not used in dev |
| .env | `.env` | `.env.dev` |

## Prerequisites

1. Docker + `docker compose` plugin installed.
2. `ngrok` installed (only if you want real YooKassa webhooks).
3. A **test Telegram bot** from [@BotFather](https://t.me/BotFather).
4. **Test credentials** in YooKassa sandbox.
5. A **test 3x-UI panel** URL/login/password.

## 1. Configure `.env.dev`

```bash
cp .env.dev.example .env.dev   # create your local dev env, fill secrets
```

Fill in at least these values:

```text
# Telegram test bot
BOT_TOKEN=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=...
URL_BOT=https://t.me/<test_bot_username>

# Test 3x-UI panel
XUI_API_URL=http://<test-panel>:2095
XUI_LOGIN=...
XUI_PASSWORD=...
XUI_SUB=http://<test-panel>:2096

# Test YooKassa
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=test_...

# Your Telegram ID for admin access
ADMIN_ID=[123456789]
ADMIN_TG_IDS=[123456789]
```

## 2. Start the dev stack

```bash
make dev-up
```

This starts:
- `postgres_dev` on `127.0.0.1:5434`
- `backend_dev` on `127.0.0.1:8000`
- `web_dev` on `127.0.0.1:8001`
- `bot_dev` (polling)

The first start initializes the DB from `bot/assets/schema_fixed.sql`; `web/run.sh` applies web migrations automatically.

## 3. Reset the dev database

Use this anytime you want a clean state:

```bash
make dev-db-reset
```

It drops and recreates `vpn_bot_dev`, then re-applies `schema_fixed.sql` and `web/migrations/*.sql`.

## 4. Expose the backend for YooKassa webhooks

YooKassa requires an HTTPS webhook URL. In dev, use **ngrok**:

```bash
# terminal 1
ngrok http 8000

# terminal 2 (after ngrok prints the HTTPS URL)
./scripts/update_ngrok_webhook.sh
```

The script:
1. Reads the current ngrok HTTPS URL from `http://127.0.0.1:4040/api/tunnels`.
2. Updates `WEBHOOK_BASE_URL` in `.env.dev`.
3. Registers the webhook in YooKassa.

If your ngrok domain changes later, re-run the script.

## 5. Useful commands

```bash
make dev-logs            # follow all dev logs
make dev-down            # stop dev stack
make dev-build           # rebuild dev images
make dev-shell-backend   # open shell in backend_dev
make dev-shell-web       # open shell in web_dev
```

## 6. Run tests

### Backend

```bash
cd backend && pytest
```

### Bot

```bash
cd bot && pytest
```

### Web

```bash
cd web && pytest
```

## 7. Safety checklist

- [ ] `.env.dev` never contains prod secrets.
- [ ] `YOOKASSA_SECRET_KEY` starts with `test_` (sandbox).
- [ ] `TELEGRAM_BOT_TOKEN` belongs to a test bot, not the prod bot.
- [ ] `XUI_API_URL` points to a test 3x-UI panel.
- [ ] Port `5434` does not conflict with prod postgres (`5433`).
- [ ] `DISABLE_WEBHOOK_IP_CHECK=true` is set only in dev.

## Troubleshooting

### `bind: address already in use` on port 8000/8001/5434

Something else is using the port. Check:

```bash
ss -tlnp | grep -E '8000|8001|5434'
```

### Bot says "Router is already attached"

This is a known polling-restart issue. Stop and start the dev bot container:

```bash
make dev-down
make dev-up
```

### YooKassa webhook returns 401

Check `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY` in `.env.dev`. Make sure the script re-ran after ngrok URL changed.
