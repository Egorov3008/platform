# Web Auth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement unified Telegram Widget authentication supporting both new users (auto-register) and existing bot users (direct login).

**Architecture:** Web layer checks if user exists in backend via `GET /users/{tg_id}`. If 404, auto-creates user via `POST /users`. Both paths converge to JWT generation and session storage.

**Tech Stack:** FastAPI, httpx (async HTTP client), Pydantic V2, pytest, PostgreSQL (backend only, no web DB changes)

---

## File Structure

**Modified Files:**
- `web/app/api/auth.py` — Update `/telegram-callback` with user existence check + auto-create logic
- `web/app/api/backend_client.py` — Add `get_user()` and `create_user()` methods
- `web/app/core/schemas.py` — Add `UserResponse` Pydantic model
- `web/tests/test_auth.py` — Add unit tests for new/existing user paths and error cases

**No new files needed.** All changes are additions to existing modules.

---

## Task Breakdown

### Task 1: Add UserResponse Pydantic Model

**Files:**
- Modify: `web/app/core/schemas.py`
- Test: `web/tests/test_auth.py`

**Context:** WebBackendClient needs a type-safe response model for user data from backend.

- [ ] **Step 1: Check existing schemas file structure**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
cat web/app/core/schemas.py | head -30
```

Expected: See existing Pydantic models (likely TelegramCallbackRequest, TokenResponse, etc.)

- [ ] **Step 2: Add UserResponse model**

Open `web/app/core/schemas.py` and add this model at the end (before or after other schemas):

```python
class UserResponse(BaseModel):
    """User data returned from backend /users endpoint"""
    tg_id: int
    is_admin: bool
    balance: float = 0.0
    server_id: Optional[int] = None
    created_at: datetime
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False
    is_blocked: bool = False
    trial: int = 0
    referral_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
```

**Add imports if missing:**
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
```

- [ ] **Step 3: Run import check**

```bash
cd web && python -c "from app.core.schemas import UserResponse; print('✓ UserResponse imported successfully')"
```

Expected: `✓ UserResponse imported successfully`

- [ ] **Step 4: Commit**

```bash
git add web/app/core/schemas.py
git commit -m "feat(web): add UserResponse pydantic model for backend user data"
```

---

### Task 2: Add get_user() and create_user() Methods to WebBackendClient

**Files:**
- Modify: `web/app/api/backend_client.py`
- Test: (tested in Task 4)

**Context:** WebBackendClient needs new methods to check if user exists and create new users.

- [ ] **Step 1: View WebBackendClient class structure**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
cat web/app/api/backend_client.py | grep -A 5 "class WebBackendClient"
```

Expected: See class definition with `__init__` and other methods like `list_keys()`, etc.

- [ ] **Step 2: Add imports at top of file**

Check if these imports exist:
```python
from httpx import HTTPStatusError
from app.core.schemas import UserResponse
```

If not, add them to the imports section.

- [ ] **Step 3: Add get_user() method**

Add this method to the `WebBackendClient` class (after existing methods like `list_keys()`):

```python
async def get_user(self, tg_id: int) -> UserResponse:
    """
    Fetch user from backend by tg_id.
    
    Args:
        tg_id: Telegram user ID
    
    Returns:
        UserResponse with user data
    
    Raises:
        HTTPStatusError(404) if user not found
        HTTPStatusError(5xx) on backend error
    """
    response = await self.client.get(
        f"/api/v1/users/{tg_id}",
        headers={"X-Bot-Secret": self.bot_secret_key}
    )
    response.raise_for_status()
    return UserResponse(**response.json())
```

- [ ] **Step 4: Add create_user() method**

Add this method right after `get_user()`:

```python
async def create_user(self, tg_id: int) -> UserResponse:
    """
    Create a new user in backend with minimal data.
    
    Auto-assigns:
    - server_id (by backend logic)
    - is_admin: false
    - balance: 0.0
    - trial: 0
    
    Args:
        tg_id: Telegram user ID
    
    Returns:
        UserResponse with created user data
    
    Raises:
        HTTPStatusError on backend error (5xx, etc.)
    """
    response = await self.client.post(
        "/api/v1/users",
        json={"tg_id": tg_id},
        headers={"X-Bot-Secret": self.bot_secret_key}
    )
    response.raise_for_status()
    return UserResponse(**response.json())
```

- [ ] **Step 5: Verify syntax**

```bash
cd web && python -c "from app.api.backend_client import WebBackendClient; print('✓ WebBackendClient imports successfully')"
```

Expected: `✓ WebBackendClient imports successfully`

- [ ] **Step 6: Commit**

```bash
git add web/app/api/backend_client.py
git commit -m "feat(web): add get_user() and create_user() methods to WebBackendClient"
```

---

### Task 3: Update /telegram-callback Endpoint Logic

**Files:**
- Modify: `web/app/api/auth.py`
- Test: (tested in Task 4)

**Context:** The main logic change. `/telegram-callback` now checks user existence and auto-creates if needed.

- [ ] **Step 1: View current /telegram-callback implementation**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
grep -A 40 "async def telegram_callback" web/app/api/auth.py
```

Expected: See current implementation that verifies CAPTCHA and generates JWT.

- [ ] **Step 2: Add import for HTTPStatusError (if not present)**

At top of `web/app/api/auth.py`, ensure this import exists:
```python
from httpx import HTTPStatusError
```

- [ ] **Step 3: Add logging import (if not present)**

Ensure this import exists:
```python
from app.core.logging import get_logger

logger = get_logger(__name__)
```

- [ ] **Step 4: Replace telegram_callback function logic**

Replace the entire `telegram_callback` function with this updated version:

```python
@router.post("/telegram-callback")
async def telegram_callback(
    request: TelegramCallbackRequest,
    backend_client: WebBackendClient = Depends(get_backend_client)
):
    """
    Handle Telegram Widget authentication callback.
    
    For new users: auto-creates in backend
    For existing users: uses existing data
    
    Both paths converge to JWT generation and session storage.
    """
    try:
        # 1. Verify CAPTCHA
        logger.debug(f"Verifying CAPTCHA: token={request.captcha_token[:8]}...")
        verify_captcha(
            request.captcha_answer,
            request.captcha_token,
            request.captcha_timestamp
        )
        logger.debug("✓ CAPTCHA verified")
        
        # 2. Verify Telegram data and extract tg_id
        logger.debug("Verifying Telegram signature...")
        tg_data = verify_telegram_data(request.telegram_data)
        tg_id = tg_data.get("id")
        
        if not tg_id:
            logger.error("No tg_id in verified Telegram data")
            raise HTTPException(
                status_code=400,
                detail="Invalid Telegram data: missing user ID"
            )
        
        logger.debug(f"✓ Telegram signature verified, tg_id={tg_id}")
        
        # 3. [NEW] Check if user exists in backend
        user = None
        try:
            logger.debug(f"Checking if user exists: tg_id={tg_id}")
            user = await backend_client.get_user(tg_id)
            logger.info(f"✓ Existing user login: tg_id={tg_id}")
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                # New user: auto-create in backend
                logger.info(f"New user detected, creating: tg_id={tg_id}")
                try:
                    user = await backend_client.create_user(tg_id)
                    logger.info(f"✓ New user created: tg_id={tg_id}")
                except HTTPStatusError as create_error:
                    logger.error(
                        f"Failed to create user: tg_id={tg_id}, "
                        f"status={create_error.response.status_code}",
                        exc_info=True
                    )
                    raise HTTPException(
                        status_code=create_error.response.status_code,
                        detail="Failed to register user"
                    )
            else:
                # Backend error (5xx, network, etc.)
                logger.error(
                    f"Backend error on user check: tg_id={tg_id}, "
                    f"status={e.response.status_code}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=503,
                    detail="Service unavailable"
                )
        
        # 4. Generate JWT with tg_id and is_admin flag
        logger.debug(f"Generating JWT: tg_id={tg_id}, is_admin={user.is_admin}")
        access_token = create_access_token(
            data={"tg_id": tg_id, "is_admin": user.is_admin}
        )
        refresh_token = create_refresh_token(
            data={"tg_id": tg_id}
        )
        logger.debug("✓ JWT tokens generated")
        
        # 5. Save session in web_users table
        logger.debug(f"Saving session: tg_id={tg_id}")
        await web_users_repo.create(
            tg_id=tg_id,
            refresh_token=refresh_token
        )
        logger.debug("✓ Session saved")
        
        # 6. Return response with HttpOnly cookies
        response = JSONResponse(
            content={
                "access_token": access_token,
                "user": {
                    "tg_id": tg_id,
                    "is_admin": user.is_admin
                }
            }
        )
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        logger.info(f"✓ Login successful: tg_id={tg_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in telegram_callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

- [ ] **Step 5: Verify imports in auth.py**

Ensure these imports exist at the top of the file:
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError
from app.api.backend_client import WebBackendClient
from app.core.logging import get_logger
from app.core.dependencies import get_backend_client
```

- [ ] **Step 6: Syntax check**

```bash
cd web && python -c "from app.api.auth import router; print('✓ auth module imports successfully')"
```

Expected: `✓ auth module imports successfully`

- [ ] **Step 7: Commit**

```bash
git add web/app/api/auth.py
git commit -m "feat(web): add user existence check and auto-creation to /telegram-callback"
```

---

### Task 4: Write Unit Tests for New Paths

**Files:**
- Modify: `web/tests/test_auth.py`

**Context:** Test the new/existing user paths, backend errors, and edge cases.

- [ ] **Step 1: View existing test_auth.py structure**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
head -50 web/tests/test_auth.py
```

Expected: See existing test fixtures and patterns (e.g., `client`, `mock_backend`).

- [ ] **Step 2: Add test for new user path**

Add this test function to `web/tests/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_telegram_callback_new_user(client, mock_backend):
    """New user: GET returns 404 → POST creates → JWT generated"""
    # Setup: User doesn't exist in backend
    from httpx import HTTPStatusError, Request, Response
    
    mock_response = Response(404)
    mock_backend.get_user.side_effect = HTTPStatusError(
        "404 Not Found",
        request=Request("GET", "http://test/users/123"),
        response=mock_response
    )
    
    # Setup: POST creates user successfully
    from app.core.schemas import UserResponse
    from datetime import datetime, timezone
    
    mock_backend.create_user.return_value = UserResponse(
        tg_id=123456,
        is_admin=False,
        balance=0.0,
        server_id=1,
        created_at=datetime.now(timezone.utc),
        username="testuser"
    )
    
    # Act: Send valid telegram callback
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {
                "id": 123456,
                "first_name": "Test",
                "hash": "valid_hash"
            },
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Login successful
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    
    # Assert: Backend was called correctly
    mock_backend.get_user.assert_called_once_with(123456)
    mock_backend.create_user.assert_called_once_with(123456)
    
    # Assert: Response contains user data
    data = response.json()
    assert data["user"]["tg_id"] == 123456
    assert data["user"]["is_admin"] is False
```

- [ ] **Step 3: Add test for existing user path**

Add this test function after the new user test:

```python
@pytest.mark.asyncio
async def test_telegram_callback_existing_user(client, mock_backend):
    """Existing user: GET returns 200 → use existing → JWT generated"""
    from app.core.schemas import UserResponse
    from datetime import datetime, timezone
    
    # Setup: User exists in backend
    mock_backend.get_user.return_value = UserResponse(
        tg_id=987654,
        is_admin=True,
        balance=100.5,
        server_id=2,
        created_at=datetime.now(timezone.utc),
        username="admin_user"
    )
    
    # Act: Send valid telegram callback
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {
                "id": 987654,
                "first_name": "Admin",
                "hash": "valid_hash"
            },
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Login successful
    assert response.status_code == 200
    assert "access_token" in response.cookies
    
    # Assert: Backend called to check, but NOT to create
    mock_backend.get_user.assert_called_once_with(987654)
    mock_backend.create_user.assert_not_called()
    
    # Assert: Response contains admin flag
    data = response.json()
    assert data["user"]["tg_id"] == 987654
    assert data["user"]["is_admin"] is True
```

- [ ] **Step 4: Add test for backend error on user check (5xx)**

Add this test:

```python
@pytest.mark.asyncio
async def test_telegram_callback_backend_error_on_check(client, mock_backend):
    """Backend error (5xx) on user check → 503 response"""
    from httpx import HTTPStatusError, Request, Response
    
    # Setup: Backend returns 500 on check
    mock_response = Response(500)
    mock_backend.get_user.side_effect = HTTPStatusError(
        "500 Internal Server Error",
        request=Request("GET", "http://test/users/123"),
        response=mock_response
    )
    
    # Act: Send callback
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 123, "first_name": "Test", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Service unavailable
    assert response.status_code == 503
    assert "Service unavailable" in response.json()["detail"]
    mock_backend.create_user.assert_not_called()
```

- [ ] **Step 5: Add test for backend error on user creation**

Add this test:

```python
@pytest.mark.asyncio
async def test_telegram_callback_backend_error_on_create(client, mock_backend):
    """Backend error (5xx) on user creation → 500 response"""
    from httpx import HTTPStatusError, Request, Response
    
    # Setup: GET returns 404 (new user)
    mock_response_404 = Response(404)
    mock_backend.get_user.side_effect = HTTPStatusError(
        "404 Not Found",
        request=Request("GET", "http://test/users/123"),
        response=mock_response_404
    )
    
    # Setup: POST fails with 500
    mock_response_500 = Response(500)
    mock_backend.create_user.side_effect = HTTPStatusError(
        "500 Internal Server Error",
        request=Request("POST", "http://test/users"),
        response=mock_response_500
    )
    
    # Act: Send callback
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 123, "first_name": "Test", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Error response
    assert response.status_code == 500
    assert "Failed to register user" in response.json()["detail"]
```

- [ ] **Step 6: Run all tests**

```bash
cd web && pytest tests/test_auth.py -v
```

Expected: All tests pass, including new and existing tests.

- [ ] **Step 7: Commit**

```bash
git add web/tests/test_auth.py
git commit -m "test(web): add unit tests for new/existing user paths and error cases"
```

---

### Task 5: Backend Verification and Endpoint Checks

**Files:**
- No modifications needed (verification only)

**Context:** Ensure backend endpoints work as expected by the web layer.

- [ ] **Step 1: Verify GET /users/{tg_id} endpoint exists**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
grep -r "def.*get.*user" backend/app/api/users.py || grep -r "@router.get" backend/app/api/ | grep users
```

Expected: See endpoint definition, e.g., `@router.get("/{tg_id}")`

- [ ] **Step 2: Check GET /users/{tg_id} returns 404 for non-existent users**

Look at `backend/app/api/users.py` and verify the response for missing users:

```bash
grep -A 15 '@router.get("/{tg_id}")' backend/app/api/users.py
```

Expected: Code includes `raise HTTPException(status_code=404)` or similar.

If status is 400 instead of 404, **note this in findings** and add to implementation notes.

- [ ] **Step 3: Verify POST /users endpoint exists**

```bash
grep -r "@router.post" backend/app/api/users.py | head -3
```

Expected: See `@router.post("/")`

- [ ] **Step 4: Check POST /users accepts minimal {tg_id} payload**

Look at request body validation:

```bash
grep -A 20 '@router.post("/$")' backend/app/api/users.py
```

Expected: Body model accepts `tg_id` field (may accept more, but tg_id is required).

- [ ] **Step 5: Verify POST /users returns 201 on success**

Check response status code:

```bash
grep -B 5 -A 10 "201\|status_code=201" backend/app/api/users.py
```

Expected: Response includes status 201 or Response model with 201.

- [ ] **Step 6: Run backend tests (if available)**

```bash
cd backend && pytest tests/api/test_users.py -v 2>&1 | head -20
```

Expected: Tests pass (or indicate what tests exist).

- [ ] **Step 7: Document findings**

Create a checklist in notes:
- [ ] GET /users/{tg_id} returns 404 for missing users
- [ ] POST /users accepts {"tg_id": N}
- [ ] POST /users returns 201 on success
- [ ] Both endpoints validate X-Bot-Secret header

---

### Task 6: Integration Test (End-to-End Verification)

**Files:**
- Create: `web/tests/test_auth_integration.py` (or add to existing integration tests)

**Context:** Test the full flow with mocked backend to verify all pieces work together.

- [ ] **Step 1: Create integration test file**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
touch web/tests/test_auth_integration.py
```

- [ ] **Step 2: Write integration test for full new user flow**

Add this to `web/tests/test_auth_integration.py`:

```python
"""Integration tests for auth flow with backend simulation"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import HTTPStatusError, Request, Response
from app.core.schemas import UserResponse
from app.api.backend_client import WebBackendClient
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_new_user_complete_flow(client, monkeypatch):
    """Full flow: new user from Telegram → check backend → create → JWT"""
    
    # Mock WebBackendClient
    mock_client = AsyncMock(spec=WebBackendClient)
    
    # Step 1: GET /users/{tg_id} returns 404
    mock_response_404 = Response(404)
    mock_client.get_user.side_effect = HTTPStatusError(
        "404 Not Found",
        request=Request("GET", "http://test/users/999"),
        response=mock_response_404
    )
    
    # Step 2: POST /users creates user
    created_user = UserResponse(
        tg_id=999,
        is_admin=False,
        balance=0.0,
        server_id=1,
        created_at=datetime.now(timezone.utc),
        username="newuser999"
    )
    mock_client.create_user.return_value = created_user
    
    # Inject mock
    from app.core.dependencies import get_backend_client
    client.app.dependency_overrides[get_backend_client] = lambda: mock_client
    
    # Act: Send login request
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 999, "first_name": "NewUser", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Success
    assert response.status_code == 200, f"Got {response.status_code}: {response.json()}"
    assert "access_token" in response.cookies
    
    # Verify backend calls
    mock_client.get_user.assert_called_once_with(999)
    mock_client.create_user.assert_called_once_with(999)
    
    # Cleanup
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_existing_user_complete_flow(client, monkeypatch):
    """Full flow: existing user from Telegram → check backend → use existing → JWT"""
    
    mock_client = AsyncMock(spec=WebBackendClient)
    
    # User exists in backend
    existing_user = UserResponse(
        tg_id=777,
        is_admin=True,
        balance=50.0,
        server_id=2,
        created_at=datetime.now(timezone.utc),
        username="existinguser"
    )
    mock_client.get_user.return_value = existing_user
    
    # Inject mock
    from app.core.dependencies import get_backend_client
    client.app.dependency_overrides[get_backend_client] = lambda: mock_client
    
    # Act: Send login request
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 777, "first_name": "Existing", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": "2"
        }
    )
    
    # Assert: Success
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_admin"] is True
    
    # Verify backend calls
    mock_client.get_user.assert_called_once_with(777)
    mock_client.create_user.assert_not_called()
    
    # Cleanup
    client.app.dependency_overrides.clear()
```

- [ ] **Step 3: Run integration tests**

```bash
cd web && pytest tests/test_auth_integration.py -v
```

Expected: Both tests pass.

- [ ] **Step 4: Commit**

```bash
git add web/tests/test_auth_integration.py
git commit -m "test(web): add integration tests for new and existing user paths"
```

---

### Task 7: Manual Testing and Verification

**Files:**
- None (manual verification only)

**Context:** Test the changes locally with running backend and web servers.

- [ ] **Step 1: Start backend server**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
```

Wait for "Uvicorn running on http://0.0.0.0:8000"

- [ ] **Step 2: Start web server**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign/web
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
```

Wait for "Uvicorn running on http://0.0.0.0:8001"

- [ ] **Step 3: Test new user path with curl (manual)**

```bash
# Simulate new user (tg_id that doesn't exist in backend)
# First, verify user doesn't exist:
curl -s -X GET http://localhost:8000/api/v1/users/99999 \
  -H "X-Bot-Secret: test_secret" | jq .

# Should return 404 or similar error
```

- [ ] **Step 4: Test telegram callback with new user**

```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_data": {"id": 99999, "first_name": "TestNew", "hash": "valid"},
    "captcha_token": "test_token",
    "captcha_timestamp": 1234567890,
    "captcha_answer": "2"
  }' | jq .
```

Expected: 200 response with `access_token` and `user` data.

- [ ] **Step 5: Check if user was created in backend**

```bash
# Should now return the created user
curl -s -X GET http://localhost:8000/api/v1/users/99999 \
  -H "X-Bot-Secret: test_secret" | jq .
```

Expected: 200 response with user data.

- [ ] **Step 6: Test existing user path**

Find an existing user (e.g., from bot usage):
```bash
curl -s -X GET http://localhost:8000/api/v1/users/<EXISTING_TG_ID> \
  -H "X-Bot-Secret: test_secret" | jq .
```

Should return 200 with existing user.

- [ ] **Step 7: Test telegram callback with existing user**

```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_data": {"id": <EXISTING_TG_ID>, "first_name": "ExistingUser", "hash": "valid"},
    "captcha_token": "test_token",
    "captcha_timestamp": 1234567890,
    "captcha_answer": "2"
  }' | jq .
```

Expected: 200 response (same as new user path).

- [ ] **Step 8: Kill servers**

```bash
pkill -f "uvicorn app.main:app"
```

- [ ] **Step 9: No commit needed**

This is manual verification only. If issues found, they're fixed in code tasks.

---

### Task 8: Documentation Update

**Files:**
- Modify: `web/CLAUDE.md` (or `web/README.md`)

**Context:** Document the new auth flow for future developers.

- [ ] **Step 1: Open web/CLAUDE.md**

```bash
cd /home/claude/vpn-platform/.claude/worktrees/web-auth-redesign
grep -n "### Authentication" web/CLAUDE.md
```

Expected: See existing auth section.

- [ ] **Step 2: Update authentication section**

Find the "### Authentication" section in `web/CLAUDE.md` and update it to include:

```markdown
### Authentication

JWT-based (python-jose):
- **Access + Refresh tokens** stored in HttpOnly cookies (`access_token`, `refresh_token`)
- **CSRF protection** via non-HttpOnly `csrf_token` cookie + `X-CSRF-Token` header
- **Login flow** (unified for new and existing users):
  1. User clicks Telegram Widget on login page
  2. Web backend receives callback: `POST /api/v1/auth/telegram-callback`
  3. Backend verifies CAPTCHA and Telegram signature
  4. **NEW:** Check if user exists in backend: `GET /api/v1/users/{tg_id}`
     - If 404 (new user): Auto-create via `POST /api/v1/users {tg_id}`
     - If 200 (existing user): Use existing data
  5. Generate JWT with `tg_id` + `is_admin` flag
  6. Save session in `web_users` table
  7. Return cookies, user logged in

**Key Design:**
- Both new and existing users use the **same Telegram Widget**
- User creation is automatic and transparent
- All user data comes from backend (web layer has no user storage)
```

- [ ] **Step 3: Verify formatting**

```bash
grep -A 20 "### Authentication" web/CLAUDE.md
```

Expected: Updated section is readable and clear.

- [ ] **Step 4: Commit**

```bash
git add web/CLAUDE.md
git commit -m "docs(web): document unified auth flow for new and existing users"
```

---

## Summary

**Total tasks:** 8
**Files modified:** 4 core files + tests + docs
**New functionality:** Transparent user auto-creation, support for existing bot users

**Key changes:**
1. `UserResponse` model added for type-safe backend user data
2. `WebBackendClient` enhanced with `get_user()` and `create_user()` methods
3. `/telegram-callback` endpoint updated with user existence check and auto-create logic
4. Comprehensive unit tests covering new/existing/error paths
5. Integration tests for end-to-end verification
6. Documentation updated

**Testing:**
- 5+ unit tests covering happy paths and error cases
- 2+ integration tests for full flows
- Manual end-to-end verification with running servers

---

## Spec Coverage Verification

✅ **Architecture section:** Covered by Task 3 (endpoint logic) and Task 2 (client methods)

✅ **Implementation details (Web API):** Covered by Task 3 and Task 1

✅ **WebBackendClient methods:** Covered by Task 2

✅ **Backend verification:** Covered by Task 5

✅ **Error handling:** Covered by Task 3 (logic with try/except) and Task 4 (error tests)

✅ **Data flow (new and existing paths):** Covered by Task 3 logic and Task 4 tests

✅ **Frontend:** No changes needed (spec requirement met)

✅ **Testing strategy:** Covered by Task 4 (unit), Task 6 (integration), Task 7 (manual)

✅ **Database:** Task 5 verifies backend schema

✅ **Deployment:** Not in implementation plan (separate process)

✅ **Monitoring:** Not in implementation plan (DevOps responsibility)

---

## No Placeholders Check

✅ All steps include exact code or exact commands
✅ No "TBD", "TODO", or "implement X" placeholders
✅ Test code is complete, not sketched
✅ All imports explicitly listed
✅ All error scenarios have exact status codes and messages
✅ All commit messages are specific and descriptive

Plan is ready for execution.
