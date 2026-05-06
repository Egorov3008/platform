# Bot Login Code Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement web-form login code generation through Telegram bot with auto-registration for new users.

**Architecture:** Bot handles `/start INVITE_TOKEN` command, validates token, checks user existence, generates code for existing users or registers new ones via backend API. All codes stored in existing `login_codes` table with 24-hour TTL.

**Tech Stack:** FastAPI (backend), python-telegram-bot (bot), PostgreSQL (existing login_codes table)

---

## File Structure

### Backend Files
- `backend/app/core/config.py` — Add INVITE_TOKEN configuration
- `backend/app/schemas/auth.py` — Add RegisterFromInviteRequest/Response schemas
- `backend/app/services/auth.py` — Add register_from_invite() service function
- `backend/app/api/v1/auth.py` — Add register-from-invite endpoint
- `tests/unit/test_auth_invite.py` — Unit tests for invite registration

### Bot Files
- `bot/.env.example` — Add INVITE_TOKEN example
- `bot/core/config.py` — Add INVITE_TOKEN to BotConfig
- `bot/handlers/start.py` — New handler for /start with invite token
- `bot/services/auth_service.py` — Auth service with code generation and user check
- `bot/api/backend_client.py` — Add register_from_invite() method (if not exists)
- `tests/test_start_handler.py` — Tests for start handler

---

## Tasks

### Task 1: Add INVITE_TOKEN to Backend Configuration

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Read current config file**

```bash
# Check the file structure
head -50 backend/app/core/config.py
```

- [ ] **Step 2: Add INVITE_TOKEN setting**

In `backend/app/core/config.py`, add to the `Settings` class:

```python
invite_token: str = Field(default="web_invite_2026", description="Token for web form invites")
```

This goes after `bot_secret_key` and before `admin_api_key` (or wherever makes sense in the file).

- [ ] **Step 3: Verify environment variable support**

Ensure `.env` can provide this value:

```bash
# Check if your Settings uses BaseSettings correctly
grep -n "class Settings" backend/app/core/config.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/config.py
git commit -m "config: add INVITE_TOKEN for web form login"
```

---

### Task 2: Create Auth Schemas for Invite Registration

**Files:**
- Modify: `backend/app/schemas/auth.py`

- [ ] **Step 1: Read current schemas**

```bash
cat backend/app/schemas/auth.py
```

- [ ] **Step 2: Add request/response schemas**

At the end of `backend/app/schemas/auth.py`, add:

```python
class RegisterFromInviteRequest(BaseModel):
    """Request to register a new user from web invite"""
    tg_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str = "en"
    invite_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "tg_id": 123456789,
                "username": "john_doe",
                "first_name": "John",
                "last_name": "Doe",
                "language_code": "en",
                "invite_token": "web_invite_2026"
            }
        }


class RegisterFromInviteResponse(BaseModel):
    """Response with generated login code"""
    tg_id: int
    login_code: str
    code_expires_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "tg_id": 123456789,
                "login_code": "ABC12345",
                "code_expires_at": "2026-04-28T12:34:56Z"
            }
        }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "schemas: add RegisterFromInviteRequest/Response"
```

---

### Task 3: Implement Register-From-Invite Service Function

**Files:**
- Modify: `backend/app/services/auth.py`

- [ ] **Step 1: Read current auth service**

```bash
cat backend/app/services/auth.py | head -100
```

- [ ] **Step 2: Add imports at top of file**

Check if already imported, add if missing:

```python
from datetime import datetime, timedelta
from backend.app.models.users.user import User
from backend.app.repositories.users import UserRepository
from backend.app.repositories.login_codes import LoginCodeRepository
from backend.app.core.security import generate_login_code
from backend.app.core.config import settings
```

- [ ] **Step 3: Add service function**

Add to `backend/app/services/auth.py` (at class level if there's an AuthService class, or as module-level function):

```python
async def register_from_invite(
    request: RegisterFromInviteRequest,
    user_repo: UserRepository,
    login_code_repo: LoginCodeRepository
) -> RegisterFromInviteResponse:
    """Register new user from web invite and generate login code"""
    
    # Validate invite token
    if request.invite_token != settings.invite_token:
        raise ValueError("Invalid invite token")
    
    # Check if user already exists
    existing_user = await user_repo.get_by_tg_id(request.tg_id)
    if existing_user:
        raise ValueError(f"User {request.tg_id} already exists")
    
    # Create user
    new_user = User(
        tg_id=request.tg_id,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        language_code=request.language_code,
        server_id=None,
        balance=0.0,
        trial=False,
        is_admin=False,
        is_blocked=False
    )
    created_user = await user_repo.create(new_user)
    
    # Generate login code
    code = generate_login_code()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Save code
    await login_code_repo.create(
        code=code,
        tg_id=created_user.tg_id,
        expires_at=expires_at
    )
    
    return RegisterFromInviteResponse(
        tg_id=created_user.tg_id,
        login_code=code,
        code_expires_at=expires_at
    )
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/auth.py
git commit -m "feat: add register_from_invite service function"
```

---

### Task 4: Add Register-From-Invite Endpoint to Backend

**Files:**
- Modify: `backend/app/api/v1/auth.py`

- [ ] **Step 1: Read current auth endpoints**

```bash
cat backend/app/api/v1/auth.py
```

- [ ] **Step 2: Add endpoint**

Add new route to `backend/app/api/v1/auth.py`:

```python
@router.post("/register-from-invite", response_model=RegisterFromInviteResponse, status_code=201)
async def register_from_invite(
    request: RegisterFromInviteRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    login_code_repo: LoginCodeRepository = Depends(get_login_code_repository),
    bot_secret: str = Header(None, alias="X-Bot-Secret")
):
    """Register new user from web invite (bot only)"""
    
    # Verify bot secret
    if not bot_secret or bot_secret != settings.bot_secret_key:
        raise HTTPException(status_code=403, detail="Invalid bot secret")
    
    try:
        result = await register_from_invite(request, user_repo, login_code_repo)
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
```

Note: Add necessary imports at top:
```python
from backend.app.schemas.auth import RegisterFromInviteRequest, RegisterFromInviteResponse
from backend.app.services.auth import register_from_invite
from backend.app.repositories.users import get_user_repository, UserRepository
from backend.app.repositories.login_codes import get_login_code_repository, LoginCodeRepository
```

- [ ] **Step 3: Run backend tests to check endpoint works**

```bash
cd backend && pytest tests/ -v -k "auth" --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/auth.py
git commit -m "endpoint: add POST /api/v1/auth/register-from-invite"
```

---

### Task 5: Write Backend Unit Tests for Invite Registration

**Files:**
- Create: `tests/unit/test_auth_invite.py`

- [ ] **Step 1: Create test file**

```python
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from backend.app.schemas.auth import RegisterFromInviteRequest, RegisterFromInviteResponse
from backend.app.services.auth import register_from_invite
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_register_from_invite_valid_token():
    """Test successful registration with valid token"""
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    
    request = RegisterFromInviteRequest(
        tg_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
        invite_token=settings.invite_token
    )
    
    # Mock user repo returning None (user doesn't exist)
    user_repo.get_by_tg_id.return_value = None
    
    # Mock created user
    mock_user = MagicMock()
    mock_user.tg_id = 123456789
    user_repo.create.return_value = mock_user
    
    # Mock login code repo
    login_code_repo.create.return_value = None
    
    result = await register_from_invite(request, user_repo, login_code_repo)
    
    assert isinstance(result, RegisterFromInviteResponse)
    assert result.tg_id == 123456789
    assert len(result.login_code) == 8
    assert result.code_expires_at > datetime.utcnow()


@pytest.mark.asyncio
async def test_register_from_invite_invalid_token():
    """Test registration fails with invalid token"""
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    
    request = RegisterFromInviteRequest(
        tg_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
        invite_token="wrong_token"
    )
    
    with pytest.raises(ValueError, match="Invalid invite token"):
        await register_from_invite(request, user_repo, login_code_repo)


@pytest.mark.asyncio
async def test_register_from_invite_user_exists():
    """Test registration fails if user already exists"""
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    
    request = RegisterFromInviteRequest(
        tg_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
        invite_token=settings.invite_token
    )
    
    # Mock existing user
    existing_user = MagicMock()
    user_repo.get_by_tg_id.return_value = existing_user
    
    with pytest.raises(ValueError, match="already exists"):
        await register_from_invite(request, user_repo, login_code_repo)
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/unit/test_auth_invite.py -v
```

Expected: All 3 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_auth_invite.py
git commit -m "test: add unit tests for register_from_invite"
```

---

### Task 6: Add INVITE_TOKEN to Bot Configuration

**Files:**
- Modify: `bot/core/config.py`
- Modify: `bot/.env.example`

- [ ] **Step 1: Read bot config**

```bash
cat bot/core/config.py
```

- [ ] **Step 2: Add INVITE_TOKEN to config**

In `bot/core/config.py`, add to config class:

```python
invite_token: str = Field(default="web_invite_2026", description="Token for web form invites")
```

- [ ] **Step 3: Update .env.example**

```bash
echo "INVITE_TOKEN=web_invite_2026" >> bot/.env.example
```

- [ ] **Step 4: Commit**

```bash
git add bot/core/config.py bot/.env.example
git commit -m "config: add INVITE_TOKEN to bot"
```

---

### Task 7: Create Bot Auth Service for Code Generation

**Files:**
- Create: `bot/services/auth_service.py`

- [ ] **Step 1: Create auth service file**

```python
import logging
from datetime import datetime, timedelta
from backend.app.schemas.auth import RegisterFromInviteRequest, RegisterFromInviteResponse
from bot.api.backend_client import BackendClient
from bot.core.config import settings
from bot.core.security import generate_login_code

logger = logging.getLogger(__name__)


class BotAuthService:
    """Handle login code generation and user registration"""
    
    def __init__(self, backend_client: BackendClient):
        self.backend_client = backend_client
    
    def validate_invite_token(self, token: str) -> bool:
        """Validate invite token"""
        return token == settings.invite_token
    
    async def get_or_register_user(self, tg_id: int, username: str | None, 
                                   first_name: str | None, last_name: str | None,
                                   language_code: str = "en") -> str:
        """
        Get login code for existing user or register new user and return code.
        Returns: login_code (8-char string)
        """
        
        # Check if user exists - try to call backend
        user_exists = await self._check_user_exists(tg_id)
        
        if user_exists:
            # Generate code locally (existing user flow)
            code = generate_login_code()
            logger.info(f"Generated code for existing user {tg_id}")
            return code
        else:
            # Register new user via backend
            logger.info(f"Registering new user {tg_id}")
            return await self._register_user_and_get_code(
                tg_id, username, first_name, last_name, language_code
            )
    
    async def _check_user_exists(self, tg_id: int) -> bool:
        """Check if user exists in system"""
        try:
            # Try to get user info from backend
            user = await self.backend_client.get_user(tg_id)
            return user is not None
        except Exception as e:
            logger.warning(f"Error checking user existence: {e}")
            return False
    
    async def _register_user_and_get_code(self, tg_id: int, username: str | None,
                                          first_name: str | None, last_name: str | None,
                                          language_code: str) -> str:
        """Register user via backend and get login code"""
        
        request = RegisterFromInviteRequest(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            invite_token=settings.invite_token
        )
        
        try:
            response: RegisterFromInviteResponse = await self.backend_client.register_from_invite(request)
            logger.info(f"Successfully registered user {tg_id}")
            return response.login_code
        except Exception as e:
            logger.error(f"Failed to register user {tg_id}: {e}")
            raise
```

- [ ] **Step 2: Commit**

```bash
git add bot/services/auth_service.py
git commit -m "feat: create auth service for code generation"
```

---

### Task 8: Add register_from_invite Method to Backend Client

**Files:**
- Modify: `bot/api/backend_client.py`

- [ ] **Step 1: Read backend client**

```bash
cat bot/api/backend_client.py | head -100
```

- [ ] **Step 2: Add register_from_invite method**

Add to the `BackendClient` class:

```python
async def register_from_invite(self, request: RegisterFromInviteRequest) -> RegisterFromInviteResponse:
    """Register new user from web invite"""
    url = f"{self.base_url}/api/v1/auth/register-from-invite"
    headers = {"X-Bot-Secret": self.bot_secret}
    
    response = await self.client.post(
        url,
        json=request.dict(),
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    return RegisterFromInviteResponse(**data)
```

Add imports if missing:
```python
from backend.app.schemas.auth import RegisterFromInviteRequest, RegisterFromInviteResponse
```

- [ ] **Step 3: Commit**

```bash
git add bot/api/backend_client.py
git commit -m "feat: add register_from_invite to BackendClient"
```

---

### Task 9: Create Bot Start Handler with Invite Token

**Files:**
- Create: `bot/handlers/start.py`

- [ ] **Step 1: Create start handler file**

```python
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.services.auth_service import BotAuthService
from bot.api.backend_client import BackendClient
from bot.core.config import settings

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional invite token"""
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Extract invite token from args if provided
    args = context.args
    invite_token = args[0] if args else None
    
    # If no token provided, show regular welcome
    if not invite_token:
        await context.bot.send_message(
            chat_id=chat_id,
            text="👋 Welcome to VPN Bot!\n\nUse /help to see available commands."
        )
        return
    
    # Validate token
    auth_service = BotAuthService(BackendClient())
    
    if not auth_service.validate_invite_token(invite_token):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid invite link.\n\nPlease check and try again."
        )
        logger.warning(f"Invalid invite token from user {user.id}: {invite_token}")
        return
    
    # Get or register user and get login code
    try:
        login_code = await auth_service.get_or_register_user(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or "en"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Your login code for the website:\n\n<code>{login_code}</code>\n\n"
                 f"This code expires in 24 hours.",
            parse_mode="HTML"
        )
        logger.info(f"Generated login code for user {user.id}")
        
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ An error occurred. Please try again later."
        )
        logger.error(f"Error generating login code for user {user.id}: {e}")
```

- [ ] **Step 2: Register handler in bot main**

Find where command handlers are registered (usually in `bot/main.py` or `bot/handlers/__init__.py`):

```python
# Add to application.add_handlers()
from bot.handlers.start import start_command

app.add_handler(CommandHandler("start", start_command))
```

Or if there's a registration function:
```python
def register_handlers(app):
    from bot.handlers.start import start_command
    app.add_handler(CommandHandler("start", start_command))
```

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/start.py
git commit -m "feat: add /start handler with invite token support"
```

---

### Task 10: Write Bot Handler Tests

**Files:**
- Create: `tests/test_start_handler.py`

- [ ] **Step 1: Create test file**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
from bot.handlers.start import start_command
from bot.core.config import settings


@pytest.mark.asyncio
async def test_start_without_invite_token():
    """Test /start without invite token shows welcome message"""
    
    # Setup
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 123456789
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456789
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.args = []  # No args
    
    # Execute
    await start_command(update, context)
    
    # Assert
    context.bot.send_message.assert_called_once()
    call_args = context.bot.send_message.call_args
    assert "Welcome" in call_args.kwargs['text']


@pytest.mark.asyncio
async def test_start_with_valid_invite_token():
    """Test /start with valid invite token generates code"""
    
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.effective_user.language_code = "en"
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456789
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.args = [settings.invite_token]
    
    with patch('bot.handlers.start.BotAuthService') as mock_auth_service:
        mock_service = MagicMock()
        mock_service.validate_invite_token.return_value = True
        mock_service.get_or_register_user = AsyncMock(return_value="ABC12345")
        mock_auth_service.return_value = mock_service
        
        await start_command(update, context)
        
        context.bot.send_message.assert_called_once()
        call_args = context.bot.send_message.call_args
        assert "ABC12345" in call_args.kwargs['text']


@pytest.mark.asyncio
async def test_start_with_invalid_invite_token():
    """Test /start with invalid token shows error"""
    
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 123456789
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456789
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.args = ["wrong_token"]
    
    with patch('bot.handlers.start.BotAuthService') as mock_auth_service:
        mock_service = MagicMock()
        mock_service.validate_invite_token.return_value = False
        mock_auth_service.return_value = mock_service
        
        await start_command(update, context)
        
        context.bot.send_message.assert_called_once()
        call_args = context.bot.send_message.call_args
        assert "Invalid" in call_args.kwargs['text']
```

- [ ] **Step 2: Run tests**

```bash
cd bot && pytest tests/test_start_handler.py -v
```

Expected: All 3 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_start_handler.py
git commit -m "test: add tests for /start handler with invite token"
```

---

### Task 11: Integration Test - Full Flow

**Files:**
- Create: `tests/integration/test_login_flow.py`

- [ ] **Step 1: Create integration test**

```python
import pytest
from httpx import AsyncClient
from backend.app.main import app
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_register_from_invite_endpoint():
    """Test /api/v1/auth/register-from-invite endpoint"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "tg_id": 999888777,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "language_code": "en",
            "invite_token": settings.invite_token
        }
        
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json=payload,
            headers={"X-Bot-Secret": settings.bot_secret_key}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tg_id"] == 999888777
        assert len(data["login_code"]) == 8
        assert "code_expires_at" in data


@pytest.mark.asyncio
async def test_register_from_invite_invalid_token():
    """Test endpoint rejects invalid invite token"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "tg_id": 999888777,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "language_code": "en",
            "invite_token": "wrong_token"
        }
        
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json=payload,
            headers={"X-Bot-Secret": settings.bot_secret_key}
        )
        
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_from_invite_missing_bot_secret():
    """Test endpoint rejects missing bot secret"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "tg_id": 999888777,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "language_code": "en",
            "invite_token": settings.invite_token
        }
        
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json=payload
            # No X-Bot-Secret header
        )
        
        assert response.status_code == 403
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && pytest tests/integration/test_login_flow.py -v
```

Expected: All 3 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_login_flow.py
git commit -m "test: add integration tests for register-from-invite flow"
```

---

### Task 12: Verify Login Code Works on Website

**Files:**
- Modify: None (manual verification)

- [ ] **Step 1: Start all services**

```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Bot
cd bot && python main.py

# Terminal 3: Web
cd web && uvicorn app.main:app --port 8001 --reload
```

- [ ] **Step 2: Test manual code generation (existing user)**

```bash
# Add a test user to backend DB
# Then in bot, start with valid invite token
# Check that code is generated and sent to user
```

- [ ] **Step 3: Test new user registration flow**

```bash
# In bot, /start with invite token as new user
# Check that user is registered and code is generated
```

- [ ] **Step 4: Test code on website**

1. Navigate to website (http://localhost:8001)
2. Click login button
3. Should redirect to bot link with invite token
4. Copy code from bot
5. Enter code on website login form
6. Should successfully login

- [ ] **Step 5: Commit final test notes**

```bash
git add -A
git commit -m "test: manual verification of login flow complete"
```

---

## Verification Checklist

- [ ] All 4 unit test files pass
- [ ] All integration tests pass
- [ ] Backend endpoint returns 201 with code for new users
- [ ] Backend endpoint returns 409 if user already exists
- [ ] Bot generates code for existing users
- [ ] Bot registers new users via API
- [ ] Website login with generated code works end-to-end
- [ ] Codes expire after 24 hours (can test with DB query)
- [ ] Invalid invite token rejected on both sides
- [ ] All commits follow conventional commits format
