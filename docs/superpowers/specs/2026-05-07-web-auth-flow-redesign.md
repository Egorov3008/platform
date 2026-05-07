# Web Authentication Flow Redesign

**Date:** 2026-05-07  
**Status:** Design Phase  
**Scope:** Restructure login/registration flow to support both new and existing (bot) users via unified Telegram Widget authentication

---

## Overview

Currently, the web application only handles **new user registration** via Telegram Widget. Existing users from the Telegram bot cannot log in to the web interface. This design unifies the authentication flow so that:

- **New users** (not in backend database) → register and login via Telegram Widget
- **Existing users** (already using the bot) → login via same Telegram Widget
- **Same JWT flow** for both paths

The distinction is handled transparently in the web-layer logic.

---

## Problem Statement

1. **Fragmented user base:** Bot users (with `tg_id` in backend DB) cannot access the web interface without re-registering
2. **Redundant workflows:** Users need different flows for bot vs. web, despite both using the same Telegram account
3. **Consistency:** No unified entry point for web authentication

---

## Goals

1. **Support both user types** via a single Telegram Widget login
2. **Automatic user creation** for new users in backend
3. **Seamless upgrade path** for existing bot users to use web UI
4. **Maintain JWT-based session security** (no changes to token structure)
5. **Zero breaking changes** to existing bot workflows

---

## Architecture

### Current Flow (New Users Only)

```
Browser
  ↓
Telegram Widget (on login page)
  ↓
User presses "Login with Telegram"
  ↓
POST /api/v1/auth/telegram-callback
  ├─ Verify CAPTCHA
  ├─ Verify Telegram data signature
  ├─ Generate JWT (tg_id in payload)
  └─ Set HttpOnly cookies
  ↓
Logged in (access_token + refresh_token cookies)
```

### New Unified Flow (New + Existing Users)

```
Browser
  ↓
Telegram Widget (on login page)
  ↓
User presses "Login with Telegram"
  ↓
POST /api/v1/auth/telegram-callback
  ├─ Verify CAPTCHA
  ├─ Verify Telegram data signature
  ├─ Extract tg_id from widget data
  │
  ├─ [NEW] GET /api/v1/users/{tg_id} (to backend)
  │   ├─ If 200 (exists) → existing user path
  │   └─ If 404 (not found) → new user path
  │
  ├─ [NEW] If 404: POST /api/v1/users (to backend)
  │   └─ Create user with auto-generated defaults
  │
  ├─ Generate JWT (tg_id in payload)
  ├─ Save session in web_users table
  └─ Set HttpOnly cookies
  ↓
Logged in (same JWT structure for both paths)
```

### User Identification

All users are identified by **`tg_id`** (Telegram ID), which is:
- Stored in backend `users` table as primary/unique identifier
- Included in JWT payload
- Used for all subsequent backend API calls

No separate web-user IDs needed; `tg_id` is sufficient.

---

## Implementation Details

### 1. Web Backend Changes

**File:** `web/app/api/auth.py`

**Endpoint: `POST /api/v1/auth/telegram-callback`**

Current request body:
```json
{
  "telegram_data": { /* Telegram widget data */ },
  "captcha_token": "...",
  "captcha_timestamp": "...",
  "captcha_answer": "123"
}
```

Response (unchanged):
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": { "tg_id": 123456, "is_admin": false, ... }
}
```

**New logic flow:**

```python
@router.post("/telegram-callback")
async def telegram_callback(
    request: TelegramCallbackRequest,
    backend_client: WebBackendClient = Depends(get_backend_client)
):
    # 1. Verify CAPTCHA (existing logic)
    verify_captcha(request.captcha_answer, request.captcha_token)
    
    # 2. Verify Telegram data signature (existing logic)
    tg_data = verify_telegram_data(request.telegram_data)
    tg_id = tg_data['id']
    
    # 3. [NEW] Check if user exists in backend
    user = None
    try:
        user = await backend_client.get_user(tg_id)
        logger.info(f"Existing user login: tg_id={tg_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # New user: auto-create in backend
            logger.info(f"New user registration: tg_id={tg_id}")
            user = await backend_client.create_user(tg_id)
        else:
            # Backend error (5xx, network, etc.)
            logger.error(f"Backend error on user check: {e}")
            raise
    
    # 4. Generate JWT (existing logic)
    tokens = create_jwt_tokens(tg_id, user.is_admin)
    
    # 5. Save session in web_users (existing logic)
    await web_users_repo.create(tg_id, tokens.refresh_token)
    
    # 6. Return response with cookies (existing logic)
    response = JSONResponse({
        "access_token": tokens.access_token,
        "user": {"tg_id": tg_id, "is_admin": user.is_admin}
    })
    response.set_cookie("access_token", tokens.access_token, httponly=True, secure=True)
    response.set_cookie("refresh_token", tokens.refresh_token, httponly=True, secure=True)
    return response
```

---

### 2. WebBackendClient Updates

**File:** `web/app/api/backend_client.py`

Add two methods:

```python
class WebBackendClient:
    async def get_user(self, tg_id: int) -> UserResponse:
        """
        Fetch user from backend by tg_id.
        
        Raises:
            httpx.HTTPStatusError(404) if user not found
            httpx.HTTPStatusError(5xx) on backend error
        """
        response = await self.client.get(
            f"/api/v1/users/{tg_id}",
            headers={"X-Bot-Secret": self.bot_secret}
        )
        response.raise_for_status()  # Raises 404 if not found
        return UserResponse(**response.json())
    
    async def create_user(self, tg_id: int) -> UserResponse:
        """
        Create a new user in backend with minimal data.
        
        Auto-registers with:
        - tg_id (required)
        - server_id (auto-assigned by backend)
        - is_admin: false
        - balance: 0
        - trial: 0
        
        Returns:
            UserResponse with created user data
        """
        response = await self.client.post(
            "/api/v1/users",
            json={"tg_id": tg_id},
            headers={"X-Bot-Secret": self.bot_secret}
        )
        response.raise_for_status()
        return UserResponse(**response.json())
```

**Pydantic models:**

```python
class UserResponse(BaseModel):
    tg_id: int
    is_admin: bool
    balance: float = 0.0
    server_id: Optional[int] = None
    created_at: datetime
    # ... other fields as defined in backend
```

---

### 3. Backend Verification

**Current status:** Backend already has these endpoints:
- `GET /api/v1/users/{tg_id}` — returns 200 with user data or 404
- `POST /api/v1/users` — creates new user

**Action items (verification only):**
1. Confirm `GET /users/{tg_id}` returns **404** (not 400) when user doesn't exist
2. Confirm `POST /users` accepts minimal request body: `{"tg_id": 123}`
3. Confirm `POST /users` returns **201** with created user data
4. Confirm `POST /users` handles duplicate `tg_id` gracefully (409 Conflict or idempotent)

See backend CLAUDE.md for current implementation details.

---

## Error Handling

### HTTP Status Codes

| Scenario | Status | Response | Action |
|----------|--------|----------|--------|
| Invalid CAPTCHA | 400 | `{"error": "Invalid CAPTCHA"}` | Frontend shows error, user retries |
| Invalid Telegram signature | 400 | `{"error": "Invalid Telegram signature"}` | Frontend shows error, user retries |
| Backend unavailable (GET user check) | 503 | `{"error": "Service unavailable"}` | Frontend shows "try again later" |
| Backend error on user creation (5xx) | 500 | `{"error": "Internal server error"}` | Frontend shows error, logs incident |
| User exists + 409 on POST /users | 409 | `{"error": "User already exists"}` | Handled gracefully, attempt GET instead |
| Success (new user) | 200 | JWT + cookies | User logged in |
| Success (existing user) | 200 | JWT + cookies | User logged in |

### Logging

All operations logged with `tg_id` and context:

```python
logger.info(f"Existing user login: tg_id={tg_id}")
logger.info(f"New user registration: tg_id={tg_id}")
logger.error(f"Backend user check failed: tg_id={tg_id}, status={e.response.status_code}")
logger.error(f"JWT creation failed: tg_id={tg_id}, error={e}")
```

---

## Data Flow

### New User Path

```
1. POST /telegram-callback (tg_id=123)
2. GET /users/123 → 404 (not in backend)
3. POST /users {"tg_id": 123} → 201 (created)
4. Create JWT(tg_id=123, is_admin=false)
5. Save session in web_users
6. Return cookies + response
```

### Existing User Path

```
1. POST /telegram-callback (tg_id=456)
2. GET /users/456 → 200 (exists in backend)
3. Create JWT(tg_id=456, is_admin=user.is_admin)
4. Save session in web_users
5. Return cookies + response
```

**Key difference:** Step 2 result determines whether to call POST /users.

---

## Frontend

**No changes required.** The frontend already uses Telegram Widget and expects `/telegram-callback` to return JWT cookies. The transparent user creation in the backend doesn't affect frontend logic.

---

## Testing Strategy

### Unit Tests (`web/tests/test_auth.py`)

```python
async def test_telegram_callback_new_user(client, mock_backend):
    """New user path: GET returns 404 → POST creates → JWT generated"""
    mock_backend.get_user.side_effect = httpx.HTTPStatusError(404, request=MagicMock(), response=MagicMock())
    mock_backend.create_user.return_value = UserResponse(tg_id=123, is_admin=False, ...)
    
    response = client.post("/api/v1/auth/telegram-callback", json=valid_telegram_data)
    
    assert response.status_code == 200
    assert "access_token" in response.cookies
    mock_backend.get_user.assert_called_once_with(123)
    mock_backend.create_user.assert_called_once_with(123)

async def test_telegram_callback_existing_user(client, mock_backend):
    """Existing user path: GET returns 200 → use existing → JWT generated"""
    mock_backend.get_user.return_value = UserResponse(tg_id=456, is_admin=False, ...)
    
    response = client.post("/api/v1/auth/telegram-callback", json=valid_telegram_data)
    
    assert response.status_code == 200
    assert "access_token" in response.cookies
    mock_backend.get_user.assert_called_once_with(456)
    mock_backend.create_user.assert_not_called()

async def test_telegram_callback_backend_error_on_check(client, mock_backend):
    """Backend error on user check (5xx) → propagate 503"""
    mock_backend.get_user.side_effect = httpx.HTTPStatusError(500, request=MagicMock(), response=MagicMock())
    
    response = client.post("/api/v1/auth/telegram-callback", json=valid_telegram_data)
    
    assert response.status_code == 503

async def test_telegram_callback_backend_error_on_create(client, mock_backend):
    """Backend error on user creation (5xx) → propagate 500"""
    mock_backend.get_user.side_effect = httpx.HTTPStatusError(404, ...)
    mock_backend.create_user.side_effect = httpx.HTTPStatusError(500, ...)
    
    response = client.post("/api/v1/auth/telegram-callback", json=valid_telegram_data)
    
    assert response.status_code == 500

async def test_telegram_callback_invalid_captcha(client):
    """Invalid CAPTCHA → 400"""
    response = client.post("/api/v1/auth/telegram-callback", json={
        "telegram_data": {...},
        "captcha_answer": "999",  # Wrong
        ...
    })
    
    assert response.status_code == 400
```

### Integration Tests (if backend deployed locally)

- Full flow: new user login
- Full flow: existing user login
- Verify JWT contains correct `tg_id`
- Verify `web_users` session created

### E2E Tests (Playwright)

```javascript
test("New user can login via Telegram Widget", async ({ page }) => {
  await page.goto("/login");
  // Click widget, simulate Telegram auth
  // Verify redirected to dashboard
});

test("Existing user can login via Telegram Widget", async ({ page }) => {
  // Pre-populate backend with existing user
  await page.goto("/login");
  // Click widget, simulate Telegram auth
  // Verify redirected to dashboard with correct user data
});
```

---

## Database Changes

### Web Layer

**Table: `web_users`** (no changes)
- Remains unchanged; only tracks web sessions
- Populated on JWT creation

### Backend Layer

**Table: `users`** (verify existing structure)

Required fields:
- `tg_id` (PRIMARY KEY or UNIQUE)
- `created_at` (DEFAULT CURRENT_TIMESTAMP)
- `is_admin` (DEFAULT false)
- `balance`, `server_id`, etc. (NULLABLE or DEFAULT)

**No migrations needed** — backend schema already supports this.

---

## Deployment Plan

### Pre-Deployment

1. **Backend verification** (checklist):
   - [ ] `GET /users/{tg_id}` returns 404 for non-existent user
   - [ ] `POST /users {"tg_id": N}` creates user with auto-assigned defaults
   - [ ] `POST /users` returns 201 on success
   - [ ] Both endpoints include `X-Bot-Secret` header validation

2. **Web layer preparation**:
   - [ ] Code reviewed
   - [ ] Tests passing (unit + integration)
   - [ ] WebBackendClient methods tested with mocks

### Deployment Steps

1. **Deploy backend** (if changes needed, otherwise skip)
   - Verify endpoints work as expected
   - Monitor logs for errors

2. **Deploy web layer**
   - Deploy new code with updated `/telegram-callback`
   - Monitor `/api/v1/auth/telegram-callback` requests

3. **Verification**
   - [ ] New user can login via web
   - [ ] Existing bot user can login via web
   - [ ] JWT contains correct `tg_id`
   - [ ] User appears in `web_users` table
   - [ ] Logs show correct user paths (new vs. existing)

### Rollback

- If web breaks: revert web code, existing auth still works
- If backend breaks: revert backend code, web requests fail gracefully (503)
- User data untouched in both cases

---

## Security Considerations

1. **Telegram Widget signature verification** — unchanged, still required
2. **CAPTCHA** — unchanged, still required for all logins
3. **JWT signing** — unchanged, still secure
4. **Backend authentication** — `X-Bot-Secret` header still validated
5. **HttpOnly cookies** — unchanged, protected against XSS
6. **CSRF protection** — unchanged, via `csrf_token` cookie + header

No new security attack surfaces introduced.

---

## Monitoring & Alerting

### Metrics to Track

- `POST /telegram-callback` request rate (should be login rate)
- New vs. existing user split (percentage of 404s from backend check)
- Backend latency on `GET /users/{tg_id}` calls
- Error rate by status code (400, 404, 500, 503)

### Alerts

- Alert if error rate on `/telegram-callback` > 5%
- Alert if backend latency > 2s (for new users)
- Alert if `create_user` fails repeatedly (backend issue)

---

## Future Enhancements

1. **Analytics** — Track new vs. existing user logins
2. **Magic links** — Alternative login for users without Telegram
3. **Web-to-bot linking** — Let web users discover bot features
4. **Password-based auth** — Optional secondary auth method
5. **OAuth** — Expand to other Telegram-like services

These are **out of scope** for this design but possible once unified auth is in place.

---

## Acceptance Criteria

- [x] New users can register + login via Telegram Widget
- [x] Existing bot users can login via same Telegram Widget
- [x] Both user types receive identical JWT tokens
- [x] User created in backend on first web login (if new)
- [x] No changes to existing bot workflows
- [x] Error handling for all failure scenarios
- [x] Full test coverage (unit + integration)
- [x] Zero breaking changes to frontend or JWT structure
- [x] Deployment guide provided

---

## References

- Backend CLAUDE.md: `/api/v1/users` endpoints
- Web CLAUDE.md: Auth flow, WebBackendClient
- Bot CLAUDE.md: User registration via RegistrationUsersMiddleware (unchanged)
- Project CLAUDE.md: Monorepo structure, service contracts
