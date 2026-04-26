# Telegram-Only Authentication Flow — Design Spec

**Date:** 2026-04-19  
**Status:** Approved  
**Scope:** vpn-web-backend (frontend + backend). Telegram bot is a separate repo and consumes a new Bot-API endpoint documented here.

---

## Context

The current system supports two registration paths: email/password (web form) and Telegram magic-link (UUID URL sent via bot). The new product requirement is a single, bot-driven registration flow:

1. User visits the website — sees a login page with a link to the Telegram bot.
2. User opens the bot in Telegram — bot generates an 8-character alphanumeric code and sends it.
3. User enters the code on the website — account is created or session resumed.
4. Session is stored in HttpOnly cookies; when it expires the user goes back to the bot for a new code.

This eliminates the email/password path and the web-triggered magic-link flow.

---

## Goals

- Single registration/login path: bot → short code → website.
- HttpOnly cookie sessions (replaces JWT in localStorage).
- Bot-facing API secured with a shared secret.
- Remove all dead code from the email/password registration path.
- Update README and CLAUDE.md to reflect the new flow.

---

## Non-Goals

- Changes to VPN key management, payments, or admin endpoints.
- Modifications to the Telegram bot codebase (only the Bot-API contract is defined here).
- Obsidian vault integration (deferred).

---

## Architecture

### Data Flow

```
Telegram Bot (separate repo)
  │
  │ POST /api/v1/bot/auth/generate-code
  │ Header: X-Bot-Secret
  │ Body: { "tg_id": 123456789 }
  │
  ▼
vpn-web-backend
  ├── Validates X-Bot-Secret
  ├── Creates row in login_codes (code, tg_id, expires_at=now+24h)
  └── Returns { "code": "X7K2M9PQ", "expires_at": "..." }

Bot sends "Ваш код для входа: X7K2M9PQ" to user in Telegram.

User on website
  │
  │ POST /api/v1/auth/login
  │ Body: { "code": "X7K2M9PQ" }
  │
  ▼
vpn-web-backend
  ├── Atomically consumes login_codes row (SET used=TRUE WHERE used=FALSE AND expires_at > NOW())
  ├── If no web_users row for tg_id: create one (email = tg_{tg_id}@bot.local, password_hash = random)
  ├── Build JWT access + refresh tokens
  └── Set-Cookie: access_token (HttpOnly, SameSite=Strict, 30min)
      Set-Cookie: refresh_token (HttpOnly, SameSite=Strict, 30d)
      Set-Cookie: csrf_token (NOT HttpOnly, SameSite=Strict, 30d)

Browser stores cookies. Subsequent requests include cookies automatically.
JS reads csrf_token cookie and sends X-CSRF-Token header on mutations.
```

---

## Database

### New table: `login_codes` (migration `002_login_codes.sql`)

```sql
CREATE TABLE login_codes (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(8)   UNIQUE NOT NULL,
    tg_id       BIGINT       NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    used        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_login_codes_tg_id   ON login_codes(tg_id);
CREATE INDEX idx_login_codes_expires ON login_codes(expires_at);
```

Code format: 8 uppercase alphanumeric characters, `secrets.token_hex` filtered to charset `[A-Z0-9]`.  
Collision check: on insert retry if UNIQUE violation (probability ~1 in 2 trillion, negligible).

### Drop: `magic_tokens` table (same migration `002`)

```sql
DROP TABLE IF EXISTS magic_tokens;
```

### `web_users` table: no schema changes

The `email` field remains `NOT NULL` but is auto-populated as `tg_{tg_id}@bot.local` when creating via code login. This is an implementation detail, not exposed to users.

---

## Backend Changes

### New file: `app/repositories/login_codes.py`

```python
class LoginCodesRepo:
    async def create(conn, tg_id: int, ttl_hours: int = 24) -> str: ...
    async def consume(conn, code: str) -> dict | None: ...  # atomic, returns row or None
```

`consume` uses a single atomic UPDATE … RETURNING to prevent TOCTOU races.

### Modified: `app/services/auth.py`

**Remove:** `register()`, `login()` (email/password), `request_magic_link()`, `verify_magic_token()`  
**Add:** `login_with_code(conn, code: str) -> tuple[str, str]`  
- Calls `LoginCodesRepo.consume()`; raises 401 if None
- Upserts `web_users` row keyed by tg_id
- Returns `(access_token, refresh_token)` via existing `_build_tokens()`

### Modified: `app/api/auth.py`

**Remove:** `POST /register`, `POST /login` (email), `POST /telegram/request`, `POST /telegram/verify`  
**Add:**
- `POST /auth/login` — calls `login_with_code`, sets cookies via `set_auth_cookies()`
- `GET  /auth/me` — reads `access_token` cookie, returns `{id, tg_id, is_admin}`
- `POST /auth/logout` — clears all three cookies
- `POST /auth/refresh` — reads `refresh_token` cookie (was reading body), issues new cookie pair

### New file: `app/api/bot.py`

```
POST /api/v1/bot/auth/generate-code
Header: X-Bot-Secret: <BOT_SECRET_KEY>
Body:   { "tg_id": 123456789 }
→ 200: { "code": "X7K2M9PQ", "expires_at": "2026-04-20T10:00:00Z" }
→ 401: if X-Bot-Secret missing or wrong
→ 404: if tg_id not found in users table
```

Router prefix: `/api/v1/bot`. Added to `app/main.py`.

### Modified: `app/core/security.py`

**Add:**
- `set_auth_cookies(response: Response, access_token: str, refresh_token: str)` — sets all three cookies
- `clear_auth_cookies(response: Response)` — expires all three cookies
- `generate_login_code() -> str` — `secrets`-based 8-char code

**Modify `get_current_user` dependency in-place:** change token source from `Authorization: Bearer` header to `access_token` cookie. Signature stays `async def get_current_user(request: Request, conn=Depends(get_conn))`. All downstream endpoints (`/keys/`, `/payments/`, `/admin/`) remain unchanged because they use `Depends(get_current_user)`.

### New: CSRF middleware (`app/core/csrf.py`)

- On every state-mutating request (POST/PUT/DELETE/PATCH): validate `X-CSRF-Token` header matches `csrf_token` cookie value.
- Exempt: `/api/v1/bot/` (uses Bot-Secret auth instead), `/api/v1/payments/webhook` (YooKassa IP-verified).
- Implementation: `starlette.middleware.base.BaseHTTPMiddleware`.

### Modified: `app/core/config.py`

```python
bot_secret_key: str           # new — shared secret for Bot-API
login_code_ttl_hours: int = 24
telegram_bot_username: str    # new — e.g. "MyVpnBot" (without @), shown on login page
```

### New migration: `migrations/002_login_codes.sql`

Creates `login_codes`, drops `magic_tokens`.

---

## Frontend Changes (`frontend/index.html`)

### Remove

- Route `#/register` and its form (email, password, tg_id fields)
- `Auth.register()` method
- `Auth.telegramRequest()` / `Auth.telegramVerify()` methods and modal
- `localStorage` token storage (`setItem`, `getItem`, `removeItem` for tokens)
- JWT decode logic in `Auth` (tokens are now opaque to JS)

### Add / Modify

**New public endpoint** `GET /api/v1/auth/config` → `{"telegram_bot_username": "MyVpnBot"}` (no auth required). Frontend calls this on page load to render the bot link.

**Login page (`#/login`):**
- Single input: "Код от бота"
- Help text: "Получите код в боте [@{bot_username}](https://t.me/{bot_username})" (populated from `/auth/config`)
- `Auth.login(code)` → `POST /api/v1/auth/login` with `{"code": "..."}` + `X-CSRF-Token` header

**`Auth` class:**
- `isLoggedIn()` → calls `GET /api/v1/auth/me`; caches result for the session
- `logout()` → calls `POST /api/v1/auth/logout`
- CSRF token: `getCsrfToken()` reads from `csrf_token` cookie (document.cookie parse)
- API client: inject `X-CSRF-Token` header on all non-GET requests

**Router:** Remove `#/register` route. Redirect `/` to `#/login` if `!Auth.isLoggedIn()`.

---

## Security Summary

| Vector | Mitigation |
|--------|-----------|
| XSS token theft | HttpOnly cookies — JS cannot access tokens |
| CSRF | `SameSite=Strict` + `X-CSRF-Token` header check |
| Code brute-force | Rate limit `/auth/login`: 5 attempts/IP/min; code expires after 24h |
| Unauthorized code generation | `X-Bot-Secret` header required on bot endpoint |
| Replay attack | `used=TRUE` atomic flag; once consumed, code is invalid |
| Telegram interception | Code expires in 24h; one-time use |

---

## Bot-API Contract (for Telegram bot team)

The Telegram bot must call this endpoint when a user requests their login code (e.g., `/start` command for new users, or a "Получить код" button for returning users whose session expired):

```
POST https://<WEBHOOK_BASE_URL>/api/v1/bot/auth/generate-code
Content-Type: application/json
X-Bot-Secret: <shared secret from config>

{
  "tg_id": 123456789
}
```

Response `200`:
```json
{
  "code": "X7K2M9PQ",
  "expires_at": "2026-04-20T10:00:00Z"
}
```

The bot should send the user a message such as:
> Ваш код для входа на сайт: **X7K2M9PQ**
> Действителен 24 часа. Введите его на странице входа.

If `tg_id` is not in the `users` table (user hasn't interacted with the bot before), the endpoint returns `404`. The bot should handle this by first ensuring the user is registered in `users` via the existing bot onboarding flow.

---

## Tests

### Unit tests to update (`tests/test_auth.py`)

- Remove: `test_register_*`, `test_login_email_*`, `test_telegram_request_*`, `test_telegram_verify_*`
- Add: `test_login_with_valid_code`, `test_login_with_expired_code`, `test_login_with_used_code`, `test_login_unknown_code`
- Add: `test_bot_generate_code_valid`, `test_bot_generate_code_bad_secret`, `test_bot_generate_code_unknown_tg_id`
- Add: `test_logout_clears_cookies`, `test_me_returns_user`, `test_refresh_rotates_cookies`

### Integration verification

1. Run `pytest` — all tests green.
2. Manual: start bot, send `/start`, receive code, open `http://localhost:8000`, enter code, verify redirect to `#/dashboard`.
3. Check DevTools → Application → Cookies: `access_token` cookie must have HttpOnly flag; `csrf_token` must NOT.
4. Verify `X-CSRF-Token` header is sent on `POST /api/v1/keys/` request.

---

## Documentation Updates

### `README.md`

- Replace "Email/Password Registration" section with new flow description.
- Add "Bot-API" section with endpoint contract.
- Add `BOT_SECRET_KEY` to environment variables table.

### `CLAUDE.md`

- Remove email/password registration from Auth description.
- Update "Two Login Flows" section: remove email/password, describe bot code flow.
- Update test patterns section to reflect cookie-based auth in tests.
- Add `BOT_SECRET_KEY`, `LOGIN_CODE_TTL_HOURS`, and `TELEGRAM_BOT_USERNAME` to Environment Variables.
