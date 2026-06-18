# Landing Page

## Overview

The landing page (`web/landing/`) is a static single-page web application that distributes **anonymous 24-hour VPN keys** for Telegram access. It is the top of a two-step acquisition funnel that ends in the existing Telegram bot. Visitors do not need to register, provide an email, or install anything beyond a VPN client app — they get a working key in roughly ten seconds.

The landing page does not replace the bot, the web SPA, or the backend. It is a small frontend surface that calls three new backend endpoints and reads a signed HTTP cookie. The funnel is intentionally asymmetric: the landing page solves an immediate pain point (Telegram is blocked right now), while the bot owns the long-term relationship (registration, trial, payments, support).

## Why a Landing Page

The Telegram channel `@DlaSvoihChanal` produces recurring news about blocks and best practices, but the conversion path is implicit — a viewer of a post has to remember the bot handle, open Telegram, type `/start`, and figure out the rest. The landing page removes the cognitive distance between "I just read that VPN is needed" and "I have a key that works." It is also a natural SEO surface for queries like "telegram not working in Russia" and "mtproto blocked," which the news channel ranks for but cannot convert from directly.

## User Journey

```
Search / Telegram channel post
   ↓
https://telegram.example.com/   ← landing page
   ↓  (one click)
POST /api/v1/landing/quick-key  ← backend issues anonymous 24h key
   ↓
Key rendered on screen + deep-links to Happ and to bot
   ↓  (after <6h remaining, CTA strengthens)
Telegram bot @TolkoDlyaSv0ih_Bot?start=landing_<uid>
   ↓
Bot registers user, marks key as converted, issues trial
   ↓
Long-term relationship in the bot
```

The temporary 24-hour key is **never deleted** when the user converts. It continues to work until its natural expiry, so a new user gets a 24-hour bonus on top of the bot's standard 14-day trial.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│ Browser                                                     │
│  ├── static HTML/CSS/JS in web/landing/                    │
│  ├── fetches /api/v1/landing/* with credentials:include     │
│  └── stores no PII; only an opaque signed cookie           │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌────────────────────────────────────────────────────────────┐
│ nginx (separate vhost for the landing domain)              │
│  ├── /  → static files from /srv/landing/                  │
│  └── /api/v1/landing/*  → proxy_pass to backend:8000       │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│ Backend (FastAPI, port 8000)                                │
│  api/v1/landing.py                                          │
│   ├── POST /quick-key  → creates anonymous 24h key          │
│   ├── GET  /state      → reads cookie, returns state        │
│   └── POST /mark-converted/{uid}  → called by bot           │
│                                                              │
│  services/core/keys/utils/{formtion,create_key}.py          │
│   └── new optional arg: inbound_id_override                 │
│                                                              │
│  config.py  ← XUI_INBOUND_ID_LANDING, LANDING_COOKIE_SECRET│
└─────────────┬──────────────────────────────┬───────────────┘
              │                              │
              ▼                              ▼
   ┌────────────────────┐         ┌──────────────────────┐
   │ 3x-UI Panel        │         │ PostgreSQL           │
   │  - landing inbound │         │  keys.landing_uid    │
   │  - add_client      │         │  keys.converted_tg_id│
   │  - limit_ip=1      │         └──────────────────────┘
   └────────────────────┘
```

The landing page is intentionally a separate vhost with its own domain. This isolates its cookies and lets the news channel link to a memorable short URL instead of a backend API path.

## Components

### Frontend: `web/landing/`

| File | Purpose |
|---|---|
| `index.html` | Single page with four `<section>` screens (new, active, expired, converted). JSON-LD FAQPage schema for Google rich snippets, OpenGraph/Twitter cards for Telegram link previews. |
| `app.js` | State machine: fetches `GET /state` on load, polls every 5 minutes, runs a one-second countdown timer on the active screen, handles the "Get key" and "Copy key" actions. |
| `style.css` | Mobile-first dark theme. Single accent color, no framework, ~300 lines. |
| `robots.txt`, `sitemap.xml` | SEO basics. |

The frontend has no build step and no runtime dependencies. It is plain vanilla JavaScript and CSS that can be served by any static file host.

### Backend: `api/v1/landing.py`

Three endpoints, all under `/api/v1/landing/`:

**`POST /quick-key`** — anonymous key issuance.

1. Generates a 16-character hex `landing_uid` and a deterministic negative `pseudo_tg_id` (hash-derived so that re-runs of the same `landing_uid` map to the same anonymous user).
2. Registers the anonymous user in `users` if it does not exist.
3. Calls the existing `build_key_services(...).create_key_svc.proces(...)` with a virtual in-memory `Tariff(id=999, amount=0, period=1, limit_ip=1)` and the new `inbound_id_override=settings.xui_inbound_id_landing`.
4. After the standard pipeline writes the key to the database, overwrites `expiry_time` with `now + 24h` and stamps `landing_uid` and `limit_ip=1`.
5. Signs a cookie `tg_landing_id` (HMAC-SHA-256, 90-day Max-Age, HttpOnly, SameSite=Lax) and sets it on the response.
6. Returns the key value, expiry timestamp, and two deep links: `happ://import/<urlencoded-config>` and the bot `t.me/<bot>?start=landing_<uid>`.

**`GET /state`** — cookie-driven state lookup.

1. Reads and verifies the `tg_landing_id` cookie. Invalid or expired cookies resolve to `state: "new"`.
2. Looks up the key by `landing_uid` from the cache, then falls back to a direct SQL query if the cache misses.
3. Returns one of five states: `new`, `active`, `expiring` (under 6 hours remaining), `expired`, or `converted` (key was claimed by a real `tg_id` through the bot).

**`POST /mark-converted/{landing_uid}`** — bot callback.

Called by the bot's `/start landing_<uid>` handler after it has decided the user is new. Sets `converted_tg_id` on the key. Does **not** delete the key from 3x-UI — the temporary 24-hour key keeps working until natural expiry.

### Database: `keys` schema extension

Two new nullable columns:

| Column | Type | Purpose |
|---|---|---|
| `converted_tg_id` | `BIGINT` | Real `tg_id` of the user who reached the bot, or `NULL` for keys still anonymous. |
| `landing_uid` | `VARCHAR(64)` | 16-char hex identifier linking the key to its signed cookie. Partial index `idx_keys_landing_uid` for fast lookups. |

The dataclass `models/keys/key.py` is updated in lockstep and both fields are added to `_DB_FIELDS` so the existing `BaseRepository` reads and writes them.

### Existing code changes

| File | Change |
|---|---|
| `services/core/keys/utils/formtion.py` | `form_new_key()` accepts optional `inbound_id_override: int \| None`. When provided, the key is created against a single forced inbound instead of the server's `inbound_ids` list. |
| `services/core/keys/utils/create_key.py` | `proces()` accepts the same parameter and forwards it. Default `None` keeps the existing call sites unchanged. |
| `api/v1/router.py` | Registers the new `landing` router. |

## Configuration

All knobs live in environment variables loaded by `config.py`:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `XUI_INBOUND_ID_LANDING` | yes | `0` | ID of the dedicated inbound in 3x-UI. Must also appear in `AVAILABLE_CONNECTIONS`. |
| `LANDING_COOKIE_SECRET` | no | falls back to `BOT_SECRET_KEY` | HMAC key for signing `tg_landing_id`. Recommended: a 64-char hex string from `openssl rand -hex 32`. |
| `LANDING_PUBLIC_URL` | no | `""` | Public URL of the landing page, used in OpenGraph and meta tags. |

The landing inbound must be added to `AVAILABLE_CONNECTIONS` in the same `.env` file. If it is not, `FormConnectionData` will not see it and key creation will fail.

## Security Considerations

- **No PII is collected.** No email, no phone, no name. The only identifier is a 16-char hex string that has no relationship to the visitor.
- **The cookie is signed, not encrypted.** The cookie payload only contains the `landing_uid` and an expiry timestamp. Tampering produces `state: "new"` because HMAC verification fails.
- **`limit_ip=1` on the 3x-UI client** restricts a single key to one concurrent device. This is enforced by 3x-UI itself, not by our code.
- **Inbound isolation.** The landing inbound is a separate 3x-UI inbound. It does not share the production inbound's IP allow-lists or rate limits. If it is abused, it can be disabled without affecting paying customers.
- **Short key lifetime.** A 24-hour key cannot be used to access anything that requires a long-lived account, and it is useless after expiry. The blast radius of any leak is small.
- **No write access to the user's account.** The bot's `/start landing_<uid>` is the only path that can attach the temporary key to a real `tg_id`. Until then, the key cannot be renewed, transferred, or queried from the user account.

## CORS

The landing page is served from a different origin than the backend. The browser must be allowed to make credentialed `POST` requests. Add the landing domain to `CORSMiddleware` in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://telegram.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

`allow_credentials=True` requires a specific origin (not `*`) and forces the browser to send the `tg_landing_id` cookie.

## Deployment

The full deployment walkthrough lives in `LANDING_DEPLOY.md` in the repository root. The short version:

1. Create a new 3x-UI inbound dedicated to the landing page. Note its ID.
2. Add `XUI_INBOUND_ID_LANDING=<id>` and `LANDING_COOKIE_SECRET=<openssl rand -hex 32>` to `.env`. Add the landing inbound ID to `AVAILABLE_CONNECTIONS`.
3. Apply the database migration: `psql $DATABASE_URL -f bot/migrations/012_add_landing_fields.sql`.
4. Copy `web/landing/` to the nginx host (e.g. `/srv/landing/`).
5. Add the nginx vhost from `LANDING_DEPLOY.md` section 3.2. Obtain a Let's Encrypt certificate.
6. Restart the backend so it picks up the new config and registers the `landing` router.
7. Open `https://telegram.example.com/` in an incognito window. The "new" screen should appear; clicking the button should switch to the "active" screen with a live countdown.

## Testing

`backend/tests/api/test_landing.py` covers the seven behaviors that do not require a live 3x-UI or database:

- `test_state_new_no_cookie` — request without a cookie returns `state: "new"`.
- `test_state_active_with_valid_cookie` — a valid cookie + a key in the cache returns `state: "active"` with the key value and deep links.
- `test_state_invalid_cookie` — a tampered cookie falls back to `state: "new"` without 401.
- `test_state_expired_key` — a key whose `expiry_time` is in the past returns `state: "expired"`.
- `test_cookie_sign_and_verify` — `sign_cookie(uid)` followed by `verify_cookie` returns the same `uid`.
- `test_cookie_verify_rejects_tampering` — a one-character change to the cookie signature makes `verify_cookie` return `None`.
- `test_pseudo_tg_id_is_negative_and_deterministic` — the derived `tg_id` is always negative and is stable across calls.

Run with:

```bash
cd backend && pytest tests/api/test_landing.py -v
```

End-to-end browser testing and live 3x-UI integration tests are not in scope; verify those by hand following `LANDING_DEPLOY.md` section 4.

## Open Items (Next Iteration)

The following are deliberately out of scope for the current MVP and live in the bot:

- `bot/handlers/start_from_landing.py` — handler for `/start landing_<uid>` with the four-case logic (new user, active keys, expired keys, no keys at all).
- `bot/api/backend_client.py` — `mark_landing_key_converted(landing_uid, tg_id)` method.
- UTM tagging and conversion analytics.
- Removing the temporary key from 3x-UI on natural expiry (the scheduler in `backend/background/` does not yet have a "sweep landing keys" job).

The `screen-converted` block in `web/landing/index.html` exists as a placeholder; it will start working automatically once the bot marks keys as converted.
