---
phase: code-review
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 37
files_reviewed_list:
  - app/api/admin.py
  - app/api/auth.py
  - app/api/keys.py
  - app/api/payments.py
  - app/api/tariffs.py
  - app/core/config.py
  - app/core/database.py
  - app/core/dependencies.py
  - app/core/security.py
  - app/core/xui.py
  - app/core/logging.py
  - app/main.py
  - app/repositories/keys.py
  - app/repositories/magic_tokens.py
  - app/repositories/payments.py
  - app/repositories/tariffs.py
  - app/repositories/users.py
  - app/repositories/web_users.py
  - app/schemas/admin.py
  - app/schemas/auth.py
  - app/schemas/keys.py
  - app/schemas/payments.py
  - app/schemas/tariffs.py
  - app/services/admin.py
  - app/services/auth.py
  - app/services/keys.py
  - app/services/payments.py
  - app/services/tariffs.py
  - app/services/dashboard_metrics.py
  - tests/conftest.py
  - tests/test_admin.py
  - tests/test_auth.py
  - tests/test_keys.py
  - tests/test_payments.py
  - tests/test_security.py
  - tests/test_tariffs.py
  - migrations/__init__.py
  - requirements.txt
  - .env.example
findings:
  critical: 5
  warning: 8
  info: 6
  total: 19
status: issues_found
---

# Code Review Report

**Reviewed:** 2026-04-11  
**Depth:** standard  
**Files Reviewed:** 37  
**Status:** issues_found

## Summary

This is a FastAPI async VPN subscription backend with JWT auth, YooKassa payments, Telegram magic-link login, and 3x-UI VPN key management. The architecture is clean and the layered pattern (api → services → repositories) is followed consistently. However, several serious security and correctness issues were found, primarily around: a TOCTOU race condition in magic-token verification that enables token reuse; IP spoofing in the webhook IP check; an unauthenticated endpoint for triggering Telegram message sends to arbitrary users; missing password strength validation; and a partial state corruption scenario if key creation fails after payment is marked succeeded. Additionally, the admin `is_admin` flag in JWTs is trusted on refresh without revalidation, the XUI singleton is not thread-safe under session expiry, and test coverage is shallow (happy-path business logic for payments and key creation is entirely untested).

---

## Critical Issues

### CR-01: TOCTOU Race Condition — Magic Token Can Be Used Twice

**File:** `app/repositories/magic_tokens.py:21-29` and `app/services/auth.py:76-91`

**Issue:** `get_valid()` (SELECT) and `mark_used()` (UPDATE) are two separate queries with no transaction or advisory lock between them. Under concurrent requests — or even a double-click — two requests can both pass the `get_valid` check before either writes `used = TRUE`. Both then call `mark_used` and proceed to issue tokens for the same magic link, bypassing the one-time-use guarantee. This allows magic-link token reuse for account takeover.

**Fix:** Perform the check-and-mark atomically using a single `UPDATE ... RETURNING` statement:
```python
# In MagicTokensRepo, replace get_valid + mark_used with a single atomic method:
async def consume(self, conn: asyncpg.Connection, token: str) -> Optional[asyncpg.Record]:
    return await conn.fetchrow(
        """
        UPDATE magic_tokens
        SET used = TRUE
        WHERE token = $1::uuid
          AND used = FALSE
          AND expires_at > NOW()
        RETURNING *
        """,
        token,
    )
```
Then in `verify_magic_token`, call `await magic_tokens_repo.consume(conn, token)` and remove the separate `get_valid` / `mark_used` calls.

---

### CR-02: Webhook IP Check Is Trivially Bypassed via X-Forwarded-For Spoofing

**File:** `app/services/payments.py:86-90`

**Issue:** The YooKassa IP check reads `request.headers.get("X-Forwarded-For", request.client.host)`. `X-Forwarded-For` is a client-supplied header; any attacker can set it to a trusted YooKassa IP. If `DISABLE_WEBHOOK_IP_CHECK` is `false`, an attacker can forge a webhook notification for any payment_id and trigger free VPN key creation:
```python
ip = request.headers.get("X-Forwarded-For", request.client.host)  # line 87 — spoofable
```

**Fix:** If a trusted reverse proxy is in use, configure the trusted proxy at the ASGI/uvicorn level using `ProxyHeadersMiddleware` and read `request.client.host` (the resolved IP) only. If no proxy, use `request.client.host` directly:
```python
# Safe: trust only the directly-connected peer, not a user-supplied header
ip = request.client.host
if not SecurityHelper().is_ip_trusted(ip):
    raise HTTPException(status_code=400, detail="Untrusted IP")
```
Or configure `uvicorn --proxy-headers --forwarded-allow-ips=<proxy_ip>` and use `request.client.host` which uvicorn will have already resolved.

---

### CR-03: Unauthenticated Telegram Message Dispatch to Arbitrary User IDs

**File:** `app/api/auth.py:37-42`, `app/services/auth.py:55-72`

**Issue:** The `/api/v1/auth/telegram/request` endpoint accepts any `tg_id` integer with no authentication and immediately sends a Telegram message to that chat ID using the bot token. There is no check that the `tg_id` belongs to a registered user, and no rate limit. An attacker can enumerate valid Telegram IDs and spam arbitrary users with messages impersonating the service, constituting unsolicited messaging abuse and a potential vector for social engineering. The created magic token is also persisted to the database for every unauthenticated call.

**Fix:** At minimum, require that `tg_id` corresponds to an existing user in the `users` table before sending:
```python
async def request_magic_link(conn: asyncpg.Connection, tg_id: int) -> None:
    user = await UsersRepo().get_by_tg_id(conn, tg_id)
    if not user:
        # Return success anyway to avoid user enumeration, but do not send
        logger.warning("Magic-link requested for unknown tg_id=%d, ignoring", tg_id)
        return
    token = await magic_tokens_repo.create(...)
    ...
```
Additionally, add rate limiting (e.g., one request per tg_id per N minutes enforced at the DB or a Redis counter).

---

### CR-04: Payment Status Marked Succeeded Before Key Creation — Partial State on Failure

**File:** `app/services/payments.py:113-139`

**Issue:** The webhook handler updates payment status to `"succeeded"` at line 113, then attempts to create the VPN key at line 135. If key creation fails (3x-UI unreachable, tariff deleted, etc.), the exception propagates and the webhook returns 500, but the payment record is already marked `"succeeded"` in the database. On YooKassa's retry of the webhook, the idempotency check at line 108 sees `status == "succeeded"` and returns early — so the key is never created. The user has paid but receives no VPN key.

```python
await payments_repo.update_status(conn, payment_id, "succeeded")  # line 113 — committed
# ...
await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)          # line 135 — can fail
```

**Fix:** Mark the payment as `"succeeded"` only after successful key creation, or use a separate intermediate status (e.g., `"processing"`) so that retries can re-attempt key creation:
```python
# Option 1: update status only after key creation succeeds
await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
await payments_repo.update_status(conn, payment_id, "succeeded")

# Option 2: use a "processing" status for retries
await payments_repo.update_status(conn, payment_id, "processing")
try:
    await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
    await payments_repo.update_status(conn, payment_id, "succeeded")
except Exception:
    await payments_repo.update_status(conn, payment_id, "key_creation_failed")
    raise
```
Also update the idempotency guard to allow re-processing of `"processing"` and `"key_creation_failed"` states.

---

### CR-05: Admin `is_admin` Escalation via Refresh Token — Config Change Not Enforced

**File:** `app/services/auth.py:94-106`

**Issue:** `refresh_tokens()` re-issues a new access token by copying `is_admin` directly from the incoming refresh token payload without re-checking `settings.admin_tg_ids`. A user who had admin status at login retains it indefinitely through refresh cycles, even after being removed from `ADMIN_TG_IDS`. More critically, if an attacker obtains an expired access token whose `is_admin` claim is `true`, they cannot use it — but if they obtain a refresh token (30-day TTL) with `is_admin=true`, they can repeatedly refresh to maintain admin access for 30 days regardless of config changes.

```python
# line 100 — is_admin is blindly copied from the attacker-supplied refresh token payload
new_payload = {"sub": payload["sub"], "tg_id": payload.get("tg_id"), "is_admin": payload.get("is_admin", False)}
```

**Fix:** Always recompute `is_admin` from the authoritative source at refresh time:
```python
async def refresh_tokens(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    tg_id = payload.get("tg_id")
    # Recompute is_admin from current config, not from token
    is_admin = _is_admin(tg_id)
    new_payload = {"sub": payload["sub"], "tg_id": tg_id, "is_admin": is_admin}
    ...
```

---

## Warnings

### WR-01: No Password Minimum Length or Complexity Validation

**File:** `app/schemas/auth.py:11-14`

**Issue:** `RegisterRequest` accepts any `password: str` with no length or complexity constraints. A single-character password is accepted. This trivially weakens account security.

**Fix:**
```python
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tg_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

---

### WR-02: XUI Singleton Not Recovered After Session Expiry

**File:** `app/core/xui.py:13-23`

**Issue:** `get_xui_client()` creates and authenticates the client once and caches it globally. If the 3x-UI session expires (the panel typically uses short-lived session cookies), subsequent API calls will fail with authentication errors. The singleton is never refreshed, so the server requires a restart to recover. `reset_xui_client()` exists but is never called on auth failure.

**Fix:** Wrap 3x-UI calls with a retry that calls `reset_xui_client()` and re-authenticates on auth error:
```python
async def get_xui_client() -> AsyncApi:
    global _xui_client
    if _xui_client is None:
        _xui_client = AsyncApi(
            host=settings.xui_api_url,
            username=settings.xui_login,
            password=settings.xui_password,
        )
        await _xui_client.login()
    return _xui_client

# In services/keys.py, wrap calls:
async def _xui_call_with_retry(coro_factory):
    try:
        return await coro_factory(await get_xui_client())
    except Exception as e:
        if "auth" in str(e).lower() or "401" in str(e) or "403" in str(e):
            await reset_xui_client()
            return await coro_factory(await get_xui_client())
        raise
```

---

### WR-03: Admin User Search Has No Pagination Limit

**File:** `app/services/admin.py:22-26`, `app/repositories/users.py:20-24`

**Issue:** When `search` parameter is provided to `GET /api/v1/admin/users`, `users_repo.search()` is called without limit/offset, returning up to 50 results. However, for every returned user, a separate `keys_repo.get_by_tg_id()` query is issued — an N+1 pattern. With 50 users this is 51 queries per request. Additionally, `search()` applies `ILIKE '%query%'` without an index, causing a full table scan on large datasets.

**Fix:** For the N+1: add a single JOIN query to count keys per user. For the scan: add a GIN/trigram index on `users.username` or rewrite to use `LIMIT` and the caller's offset parameters:
```python
# repositories/users.py
async def search(self, conn, query: str, limit: int = 50, offset: int = 0):
    return await conn.fetch(
        "SELECT u.*, COUNT(k.client_id) AS keys_count "
        "FROM users u LEFT JOIN keys k ON u.tg_id = k.tg_id "
        "WHERE u.username ILIKE $1 OR u.tg_id::text = $2 "
        "GROUP BY u.tg_id LIMIT $3 OFFSET $4",
        f"%{query}%", query, limit, offset,
    )
```

---

### WR-04: `create_key` Called Without Payment Verification from User-Facing Endpoint

**File:** `app/api/keys.py:40-48`

**Issue:** `POST /api/v1/keys/` calls `keys_service.create_key()` directly with `tariff_id` from the request body. There is no check that the calling user has an associated payment for that tariff, nor any check that the tariff has `amount == 0` (free tier) before permitting creation. Any authenticated user with a `tg_id` can create unlimited keys on any paid tariff for free by calling this endpoint directly, bypassing the payment flow entirely.

**Fix:** Either remove the unauthenticated key creation endpoint (require all paid-tariff keys to go through `/payments/create` → webhook), or add a check:
```python
@router.post("/", response_model=KeyResponse)
async def create_key(body: CreateKeyRequest, conn=Depends(get_conn), current_user=Depends(get_current_user)):
    tg_id = _require_tg_id(current_user)
    tariff = await tariff_service.get_by_id(conn, body.tariff_id)
    if tariff["amount"] > 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Paid tariffs require payment via /payments/create"
        )
    return await keys_service.create_key(conn, tg_id, body.tariff_id)
```

---

### WR-05: Subscription URL Leaks XUI Internal API URL

**File:** `app/services/keys.py:101`

**Issue:** The `key` field stored in the database and returned to the user is constructed as:
```python
subscription_url = f"{settings.xui_api_url}/sub/{email}"
```
`xui_api_url` is the internal admin panel URL (e.g., `https://host:2096`). This exposes the VPN panel's management port and host to all users. The subscription URL format for XRay clients is typically different from the admin panel URL.

**Fix:** Use a dedicated `XUI_SUBSCRIPTION_URL` environment variable that points to the public subscription endpoint (which may be on a different port or path), separate from `XUI_API_URL`:
```python
# config.py
xui_subscription_url: str  # e.g. https://vpn.example.com/sub

# services/keys.py
subscription_url = f"{settings.xui_subscription_url}/{email}"
```

---

### WR-06: `SensitiveDataFilter` Only Masks Log Message, Not `args`

**File:** `app/core/logging.py:26-38`

**Issue:** Python's `logging` module lazily formats messages: the actual log output is `record.msg % record.args`. The filter only masks `record.msg` (the format string), not `record.args` (the interpolation arguments). If a password or token value appears as a positional argument to a logger call (e.g., `logger.info("Token: %s", token_value)`), the filter will not mask it because the raw value lives in `record.args`, not in `record.msg`.

**Fix:**
```python
def filter(self, record: logging.LogRecord) -> bool:
    # Format the full message before scanning
    if record.args:
        try:
            full_msg = record.getMessage()  # formats msg % args
            record.msg = full_msg
            record.args = ()
        except Exception:
            pass
    if isinstance(record.msg, str):
        import re
        for _, pattern in self.SENSITIVE_PATTERNS:
            try:
                record.msg = re.sub(pattern, r'\1***MASKED***\2', record.msg)
            except re.error:
                pass
    return True
```

---

### WR-07: `admin_tg_ids` Accepts Unvalidated User-Supplied `tg_id` During Registration

**File:** `app/services/auth.py:23-24`, `app/schemas/auth.py:13`

**Issue:** `RegisterRequest` accepts a caller-supplied `tg_id: Optional[int]`. This `tg_id` is passed to `_is_admin()` which checks it against `settings.admin_tg_ids`. A user who knows an admin's Telegram ID can register a web account claiming that `tg_id` and receive a JWT with `is_admin: true`. There is no check that the supplied `tg_id` actually belongs to the registering user or that it is not already registered.

```python
# auth.py line 41 — tg_id from request body used to determine admin status
user = await web_users_repo.create(conn, email=email, password_hash=hash_password(password), tg_id=tg_id)
return _build_tokens(user["id"], tg_id)  # tg_id could be any admin's ID
```

**Fix:** Do not allow arbitrary `tg_id` to be claimed at registration. Remove `tg_id` from `RegisterRequest` entirely; tg_id linkage should only happen through the verified magic-link flow:
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    # tg_id removed — link via /auth/telegram/verify after registration
```

---

### WR-08: Webhook Handler Returns 200 OK on Key Creation Failure, Suppressing YooKassa Retry

**File:** `app/services/payments.py:134-139`

**Issue:** When `create_key` raises an exception, the exception propagates out of `handle_webhook`, causing `payment_webhook` to return a 500 error. However, the payment is already marked `"succeeded"` (CR-04). On the next retry from YooKassa, the idempotency check (`existing["status"] == "succeeded"`) short-circuits and returns early. So even if the exception is fixed, the user never gets their key. This is a compound of CR-04 but also worth noting independently: the error handling strategy (re-raise) defeats YooKassa's retry mechanism.

**Fix:** See CR-04. Additionally, make the webhook always return 200 to YooKassa (as required by their docs) and handle failures internally with alerting:
```python
try:
    await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
except Exception as e:
    logger.error("Key creation failed for payment %s: %s", payment_id, e)
    # Alert via monitoring; do not raise — return 200 to YooKassa
    # Mark payment as needing manual intervention
    await payments_repo.update_status(conn, payment_id, "key_creation_failed")
```

---

## Info

### IN-01: `_expiry_ms` `months` Parameter Is Unused

**File:** `app/services/keys.py:23-27`

**Issue:** `_expiry_ms(period_days, months=1)` multiplies `period_days * months`, but every call site passes only `period_days`: `_expiry_ms(tariff["period"])`. The `months` parameter appears to be dead code intended for multi-month subscription purchases that was never wired up.

**Fix:** Remove the `months` parameter, or wire it up from the call sites if multi-month subscriptions are intended.

---

### IN-02: Incomplete Log Message — Typo in Registration Log

**File:** `app/api/auth.py:25`

**Issue:** `logger.info("Пользователь успешно зарегистри: tg_id=%s", ...)` — the word "зарегистрирован" is truncated to "зарегистри". Minor but indicates the log line was not reviewed.

**Fix:** `logger.info("Пользователь успешно зарегистрирован: tg_id=%s", ...)`

---

### IN-03: `admin.py` Imports Nonexistent `DashboardMetricsService` Path

**File:** `app/api/admin.py:17`

**Issue:** The import `from app.services.dashboard_metrics import DashboardMetricsService` references a file (`app/services/dashboard_metrics.py`) that is not in the changed file list and is not a standard part of the declared architecture. If this file does not exist in the deployed environment the application will fail to start with `ImportError`. The file was found in the working tree but is absent from `app/services/__init__.py` exports and from the git-tracked changes.

**Fix:** Ensure `app/services/dashboard_metrics.py` is committed and included in the deployment. Add it to `app/services/__init__.py` or document it as an intentional standalone module.

---

### IN-04: `keys.store()` Uses `time.time()` for `created_at` Instead of Database `NOW()`

**File:** `app/repositories/keys.py:43-53`

**Issue:** `created_at` is set in Python with `int(time.time() * 1000)` and passed as a query parameter. Using application-side timestamps is less reliable than `DEFAULT NOW()` or `CURRENT_TIMESTAMP` at the database level — clock skew between app servers, or differences in timezone handling can cause inconsistencies. Other timestamp fields in `users` and `payments` appear to use database-side defaults.

**Fix:** Remove the `created_at` parameter and use a database default:
```sql
-- In schema: created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW()) * 1000
```
```python
# Remove created_at from INSERT and the import of time
return await conn.fetchrow(
    "INSERT INTO keys (tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date) "
    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *",
    tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date,
)
```

---

### IN-05: `pytest-asyncio` Mode Not Configured — Tests May Use Wrong Event Loop Policy

**File:** `requirements.txt`, `tests/`

**Issue:** `pytest-asyncio==0.24.0` is installed but there is no `pytest.ini`, `pyproject.toml`, or `setup.cfg` configuring `asyncio_mode = "auto"`. In version 0.21+, `pytest-asyncio` defaults to `"strict"` mode, requiring explicit `@pytest.mark.asyncio` on every async test and explicit `asyncio_mode` config. Async fixtures (e.g., `async def client(...)`) also require `@pytest_asyncio.fixture`. Without this configuration, async fixtures may silently fall back to sync behavior or emit deprecation warnings that become errors in future versions.

**Fix:** Add to a `pytest.ini` or `pyproject.toml`:
```ini
[pytest]
asyncio_mode = auto
```
And change async fixtures from `@pytest.fixture` to `@pytest_asyncio.fixture` in all test files.

---

### IN-06: Shallow Test Coverage — Core Business Logic Untested

**File:** `tests/test_payments.py`, `tests/test_keys.py`, `tests/test_admin.py`

**Issue:** The payment tests only check that unauthenticated requests are rejected (HTTP 403) and that invalid JSON returns 400. The entire webhook processing path — including the idempotency check, payment_type parsing, and key creation trigger — has zero test coverage. Similarly, key creation, renewal, and admin key force-delete have no tests covering their success paths. The admin tests only verify that unauthenticated requests return 403. This means the critical payment → key provisioning pipeline (the core business function) has never been exercised by the test suite.

**Fix:** Add integration-level tests for:
- Successful webhook processing with `PAYMENT_SUCCEEDED` event (mock `PaymentsRepo` and `create_key`)
- Idempotency: second webhook call with same `payment_id` is a no-op
- `create_key` success and 3x-UI error handling (mock `get_xui_client`)
- `renew_key` ownership check (different `tg_id` returns 404)
- Admin force-delete key flow

---

_Reviewed: 2026-04-11_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_
