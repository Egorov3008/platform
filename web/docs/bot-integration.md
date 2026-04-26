# Backend ↔ Telegram Bot Integration

This document maps the web backend (`vpn-web-backend`) to the Telegram bot (`Bot_3xui_vpn`) business logic. Both systems share the same PostgreSQL database and 3x-ui VPN panel but operate independently.

---

## Architecture Overview

```
┌─────────────────────┐        ┌──────────────────────────┐
│   Telegram Bot      │        │   Web Backend (FastAPI)  │
│  Bot_3xui_vpn/      │        │  vpn-web-backend/        │
│                     │        │                          │
│  handlers/          │        │  app/api/                │
│  services/core/     │        │  app/services/           │
│  payments/          │        │  app/repositories/       │
└────────┬────────────┘        └─────────────┬────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                     │
│  users · web_users · keys · tariffs · payments          │
│  login_codes · inbounds · servers · referral_*          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │    3x-ui VPN Panel     │
         │   (XRay/V2Ray keys)    │
         └────────────────────────┘
```

---

## 1. Shared Database Tables

| Table | Bot | Backend |
|-------|-----|---------|
| `users` | **Owner**: creates/updates on `/start`. Fields: `tg_id`, `username`, `trial`, `balance`, `referral_id` | Read-only via `users_repo.get_by_tg_id()` in `app/repositories/users.py` |
| `web_users` | — | **Owner**: creates on first web login. Links `tg_id` to web session |
| `login_codes` | Creates via `POST /api/v1/bot/auth/generate-code` *(planned)* | Consumes atomically in `login_codes_repo.consume()` at `app/repositories/login_codes.py` |
| `keys` | **Owner**: creates via `CreateKey`, updates via `KeyRenewal`, deletes old via `XUISession.delete_old_client()` | Full CRUD: `app/repositories/keys.py` |
| `tariffs` | Read-only via `TariffData` | Read-only via `app/repositories/tariffs.py` |
| `payments` | **Owner**: creates via `YooKassService.create_payment_form()`, updates via aiohttp webhook at `/webhook` | Creates via `POST /api/v1/payments/create`, updates via `POST /api/v1/payments/webhook` |
| `inbounds` | **Owner**: manages inbound assignments | Read-only (not used by backend) |
| `servers` | **Owner**: manages server list | Read-only (backend uses env vars directly) |

---

## 2. Authentication Integration

The only direct HTTP call between systems: the bot calls the backend to generate a one-time login code.

```
┌─────────────┐   POST /api/v1/bot/auth/generate-code   ┌─────────────────┐
│ Telegram    │ ─────────────────────────────────────── │ Web Backend     │
│ Bot         │   Header: X-Bot-Secret: <BOT_SECRET_KEY> │                 │
│             │   Body: {"tg_id": 123456789}            │                 │
│             │ ◄──────────────────────────────────────  │                 │
│             │   {"code": "A1B2C3D4",                  │ login_codes     │
│             │    "expires_at": "2026-04-21T10:00:00Z"} │ table (24h TTL) │
└──────┬──────┘                                         └─────────────────┘
       │ Sends code to user via Telegram message
       ▼
  User sees: "Your login code: A1B2C3D4"
       │
       │ User enters code at web portal
       ▼
┌─────────────────┐
│ POST /api/v1/auth/login  {"code": "A1B2C3D4"}    │
│ → login_codes_repo.consume()  (atomic, single-use)│
│ → web_users_repo.get_by_tg_id() or create()       │
│ → issues access_token + refresh_token cookies      │
└─────────────────────────────────────────────────────┘
```

**Backend endpoint**: `app/api/bot.py` — `POST /api/v1/bot/auth/generate-code`
- Auth: `X-Bot-Secret` header validated against `settings.bot_secret_key`
- Returns 404 if `tg_id` not found in `users` table (bot must register user first)

**Bot integration point**: The bot should call this endpoint when a user requests a web cabinet link (e.g., from the profile dialog). This call is not yet implemented in the bot — the endpoint was designed for it.

---

## 3. VPN Key Operations

Both systems create and manage VPN keys independently. The data formats must match exactly.

### Shared Key Fields

| Field | Format | Example |
|-------|--------|---------|
| `client_id` | UUID v4 string | `"550e8400-e29b-41d4-a716-446655440000"` |
| `email` | `{tg_id}_{uuid}@domain.com` | `"123456_abc@domain.com"` |
| `expiry_time` | Unix ms epoch (integer) | `1745000000000` |
| `total_gb` | GB as float | `50.0` (0 = unlimited) |
| `limit_ip` | Max simultaneous connections | `3` |

### Key Creation Comparison

**Bot** (`Bot_3xui_vpn/services/core/keys/utils/create_key.py`):
```
CreateKey.proces(tg_id, tariff, server_id)
  → FormationKey.form_new_key()      # generates email, client_id, expiry_ms
  → XUISession.add_client()          # POST to 3x-ui panel (3 retries, 2s interval)
  → DB save via asyncpg
  → Cache update: key_{email}
```

**Backend** (`vpn-web-backend/app/services/keys.py`):
```
create_key(conn, tg_id, tariff_id)
  → _random_email()                  # generates UUID-based email
  → _expiry_ms(period_days)          # calculates expiry timestamp
  → _xui_add_client(api, ...)        # POST to same 3x-ui panel
  → keys_repo.store(conn, ...)       # INSERT into keys table
```

### Key Renewal Comparison

**Bot** (`Bot_3xui_vpn/services/core/keys/`):
```
KeyRenewal → KeyUpdater.refresh_key()
  → XUISession.extend_client_key()   # updates expiry + traffic in 3x-ui
  → KeyResetter.reset_key_after_renewal()  # clears notification flags
  → DB + cache update
```

**Backend** (`vpn-web-backend/app/services/keys.py`):
```
renew_key(conn, client_id, tg_id, tariff_id)
  → keys_repo.get_by_client_id()     # fetch current key
  → _xui_update_client(api, ...)     # same 3x-ui API call
  → keys_repo.update_expiry(conn, ...)  # UPDATE expiry_time, tariff_id, total_gb
```

> **Warning**: Both systems may modify the same VPN key (identified by `client_id`) without coordination. Concurrent operations (e.g., bot renews while web deletes) can cause inconsistency. No distributed lock exists.

---

## 4. Payment Flows

Two parallel payment flows use the **same YooKassa account** but different `payment_type` prefixes so each system recognizes its own payments.

### Bot Payment Flow

```
User selects tariff → PaymentState.setting_pay
  → YooKassService.create_payment_form(price, description)
     [Bot_3xui_vpn/payments/pay_config.py]
  → payments table: payment_type = "create_key|{tariff_id}"
                               or "renew_key|{email}"
  → YooKassa returns confirmation_url
  → User redirected to payment page

YooKassa → POST /webhook  (aiohttp server, separate port)
  [Bot_3xui_vpn/payments/pyments_webhook.py]
  → PAYMENT_SUCCEEDED:
      PaymentRouter.route(payment_id)
        "create_key|{tariff_id}" → KeyCreationService.process()
        "renew_key|{email}"      → KeyRenewalService.process()
  → PAYMENT_WAITING_FOR_CAPTURE → Payment.capture()
  → PAYMENT_CANCELED → update status
```

### Web Backend Payment Flow

```
User clicks "Pay" → POST /api/v1/payments/create
  [vpn-web-backend/app/api/payments.py]
  → payments_service.create_payment(conn, tg_id, tariff_id)
     [vpn-web-backend/app/services/payments.py]
  → payments table: payment_type = "web_new_key|{tg_id}:{tariff_id}"
  → YooKassa returns payment_url → returned to frontend

YooKassa → POST /api/v1/payments/webhook
  [vpn-web-backend/app/api/payments.py]
  → PAYMENT_SUCCEEDED:
      parse payment_type: "web_new_key|{tg_id}:{tariff_id}"
      → keys_service.create_key(conn, tg_id, tariff_id)
```

### payment_type Format Reference

| System | Operation | Format | Example |
|--------|-----------|--------|---------|
| Bot | Create new key | `create_key\|{tariff_id}` | `create_key\|10` |
| Bot | Renew key | `renew_key\|{email}` | `renew_key\|123456_abc@domain.com` |
| Backend | Create new key | `web_new_key\|{tg_id}:{tariff_id}` | `web_new_key\|123456789:10` |

Each system skips payments with unknown prefixes — there is no cross-processing.

---

## 5. User Table Relationships

```
users (bot-owned)          web_users (backend-owned)
┌──────────────────┐       ┌──────────────────────────┐
│ tg_id (PK)       │◄──────│ tg_id (FK, unique)       │
│ username         │       │ id (PK)                  │
│ trial (0/1)      │       │ email                    │
│ balance          │       │ password_hash            │
│ referral_id      │       │ created_at               │
│ check_referral   │       └──────────────────────────┘
│ is_blocked       │
│ server_id        │       keys (shared)
└──────────────────┘       ┌──────────────────────────┐
         │                 │ tg_id (FK → users.tg_id) │
         └────────────────►│ client_id                │
                           │ email                    │
                           │ key (VLESS URL)          │
                           │ expiry_time              │
                           │ tariff_id                │
                           └──────────────────────────┘
```

- `users` is created and managed exclusively by the bot on `/start`
- `web_users` is created by the backend on first successful login (linked by `tg_id`)
- VPN key operations in the backend require `tg_id` to exist in `users` — the backend returns **404** if the user hasn't started the bot yet
- Bot `trial`, `balance`, `referral_id` fields are never written by the backend

---

## 6. Background Notifications (Bot-only)

The bot runs background notification funnels every hour, reading from shared DB tables:

| Funnel | Reads | Sends |
|--------|-------|-------|
| `KeyExpiry24h` | `keys.expiry_time` | "Your key expires in 24 hours" + "Renew" button |
| `KeyExpiry10h` | `keys.expiry_time` | "Your key expires in 10 hours" + "Renew" button |
| `TrialReminder` | `users.trial`, `keys.expiry_time` | "Trial ending, upgrade now" |
| `ReferralReminder` | `users.referral_id` | "Earn money inviting friends" |
| `ColdLeadEngagement` | `users.created_at`, activity | "We miss you!" |

"Renew" buttons in notifications deep-link to the Telegram bot (not the web portal). Users renewing from a notification enter the bot's payment flow, not the backend's.

---

## 7. 3x-ui Panel Shared Access

Both systems call the **same 3x-ui panel** with the **same credentials**.

| | Bot | Backend |
|--|-----|---------|
| Client | `XUISession` wrapping `py3xui.AsyncApi` | `AsyncApi` lazy singleton in `app/core/xui.py` |
| Auth | `ensure_auth()` with retry | Session-based login on each operation |
| Retry policy | 3 attempts, 2s interval | None (single attempt) |
| Operations | add, extend, delete, get_traffic, get_inbounds | add, update, delete |
| Metrics | Prometheus counters per method | None |

**Concurrency risk**: No distributed lock guards key operations. If a user simultaneously triggers key renewal from the bot and deletion from the web portal, both will call 3x-ui without coordination.

---

## 8. Shared Environment Variables

Both projects must be configured with identical values for these:

| Variable | Used by | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | Both | Same PostgreSQL instance |
| `YOOKASSA_SHOP_ID` | Both | Same YooKassa merchant account |
| `YOOKASSA_SECRET_KEY` | Both | Same YooKassa credentials |
| `XUI_API_URL` | Both (backend: `XUI_API_URL`) | Same 3x-ui panel URL |
| `XUI_LOGIN` / `XUI_PASSWORD` | Both | Same panel credentials |
| `XUI_INBOUND_ID` | Backend | Default inbound for web-created keys |
| `BOT_SECRET_KEY` | Backend | Validates `X-Bot-Secret` header from bot |
| `BOT_TOKEN` | Bot (+ backend for config endpoint) | Telegram bot token |
| `TELEGRAM_BOT_USERNAME` | Backend | Displayed on login page |
| `ADMIN_TG_IDS` | Backend | JSON array; bot uses `ADMIN_ID` |

---

## 9. Integration Checklist for New Features

When adding a feature that touches shared data:

- [ ] **Keys**: Does the feature change `expiry_time` or `total_gb`? Both systems must use the same field format (ms epoch, float GB).
- [ ] **Payments**: Is a new `payment_type` prefix needed? Add it to both systems' webhook handlers or document which system handles it.
- [ ] **Users**: Only the bot creates `users` rows. Backend features that need user data must check the user exists first.
- [ ] **Notifications**: If the backend creates a key, the bot's expiry notification funnels will automatically pick it up — no extra wiring needed.
- [ ] **3x-ui**: Any key operation from the web must use `client_id` as the stable identifier (same UUID stored in the `keys` table by both systems).
