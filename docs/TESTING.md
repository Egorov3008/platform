<!-- generated-by: gsd-doc-writer -->
# Testing

The VPN platform has three separate test suites — one per component — each using pytest with `asyncio_mode = auto`. The web component additionally has a Playwright-based E2E suite.

## Test Framework and Setup

| Component | Framework | Version | Config file |
|---|---|---|---|
| `backend/` | pytest + pytest-asyncio | pytest >= 8.0.0, pytest-asyncio >= 0.24.0 | `backend/pytest.ini` |
| `bot/` | pytest + pytest-asyncio + pytest-cov | pytest == 9.0.2, pytest-asyncio == 1.3.0 | `bot/pytest.ini` |
| `web/` (unit) | pytest + pytest-asyncio | pytest >= 8.0.0, pytest-asyncio >= 0.24.0 | `web/pytest.ini` |
| `web/` (E2E) | Playwright (Python sync API) + pytest-playwright | playwright >= 1.42.0 | `web/pytest.ini` (testpaths includes `tests_e2e`) |

All three components set `asyncio_mode = auto`, so async test functions do not need the `@pytest.mark.asyncio` decorator added explicitly (though it is used in backend tests for clarity).

**Before running tests**, install each component's dependencies:

```bash
# Backend
cd backend && pip install -r requirements.txt

# Bot
cd bot && pip install -r requirements.txt

# Web (unit)
cd web && pip install -r requirements.txt

# Web (E2E) — also requires a running web server and database
cd web/tests_e2e && pip install -r requirements.txt
```

For E2E tests, install Playwright browsers:

```bash
cd web/tests_e2e && playwright install
```

## Running Tests

### Backend

```bash
# All backend tests
cd backend && pytest

# Single test file
cd backend && pytest tests/api/test_keys.py

# Single test by name
cd backend && pytest tests/api/test_keys.py::test_list_keys
```

### Bot

```bash
# All bot tests
cd bot && pytest

# Single module
cd bot && pytest tests/models/

# Single test by name
cd bot && pytest -k test_name

# With coverage report
cd bot && pytest --cov
```

### Web (unit)

```bash
# All web unit tests
cd web && pytest tests/

# Single test file
cd web && pytest tests/test_auth.py

# Single test by name
cd web && pytest tests/test_auth.py::test_register
```

### Web (E2E)

E2E tests require a running web server and a populated PostgreSQL database.

```bash
# All E2E tests (headless Chromium)
cd web && npx playwright test

# Headed mode (visible browser window)
cd web/tests_e2e && playwright test --headed

# Single E2E file
cd web/tests_e2e && playwright test test_auth.py

# Specific feature suites
cd web/tests_e2e && playwright test test_dashboard.py
cd web/tests_e2e && playwright test test_tariffs_payments.py
cd web/tests_e2e && playwright test test_admin.py
cd web/tests_e2e && playwright test test_routing.py
cd web/tests_e2e && playwright test test_ui_ux.py
```

The bot's `pytest.ini` enables verbose output with short tracebacks by default (`-v --tb=short`).

## Writing New Tests

### File Naming Conventions

All three components follow the same convention:

- Files: `test_*.py` (e.g., `test_keys.py`, `test_auth.py`)
- Classes: `Test*` (optional — most tests use plain functions)
- Functions: `test_*`

Test files live in the `tests/` directory of each component, organized by area:

```
backend/tests/
    api/              # HTTP endpoint tests
    test_health.py
    test_readiness.py

bot/tests/
    models/           # Pydantic model tests
    middlewares/      # Middleware unit tests
    services/         # Business service tests
        cache/
        keys/
        notification/
        analytics/
        synchron/
        ...
    dialogs/          # Dialog factory and getter tests
    handlers/         # Handler flow tests
    database/         # Repository and data service tests
    registration/     # Registration flow tests
    scenarios/        # End-to-end scenario tests (in-process)
    api/              # BackendAPIClient tests
    payments/         # Payment webhook tests

web/tests/
    test_auth.py
    test_keys.py
    test_tariffs.py
    test_payments.py
    test_admin.py
    test_csrf.py
    test_security.py
    test_backend_client.py
    ...

web/tests_e2e/
    test_auth.py
    test_dashboard.py
    test_tariffs_payments.py
    test_admin.py
    test_routing.py
    test_ui_ux.py
```

### Test Helpers and Fixtures

**Backend** (`backend/tests/api/conftest.py`):

The `api_client` fixture wraps the FastAPI app with `AsyncClient` (ASGI transport) and overrides all dependencies:

```python
@pytest.fixture
async def api_client(mock_service_data):
    app.dependency_overrides[get_service_data] = lambda: mock_service_data
    app.dependency_overrides[get_pool] = lambda: AsyncMock()
    app.dependency_overrides[get_cache] = lambda: MagicMock()
    app.dependency_overrides[verify_bot_secret] = lambda: None
    app.dependency_overrides[verify_api_key] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
```

The `mock_service_data` fixture provides `AsyncMock` stubs for all service layer calls (`tariffs`, `users`, `keys`, `payments`, `servers`).

**Bot** (`bot/tests/conftest.py`):

Shared fixtures include `mock_cache` (an `AsyncMock` of `CacheService`), `mock_conn` (an `AsyncMock` of `asyncpg.Pool`), `data_service` (an `AsyncMock` of `DataService`), `mock_xui_session`, `mock_dialog_manager`, and model instance fixtures (`user`, `key`, `tariff`, `payment`, `inbound`, `server`, `gift_link`).

**Web unit** (`web/tests/conftest.py`):

The `mock_conn` fixture stubs `asyncpg` pool operations. The `disable_csrf` fixture is `autouse=True` and disables CSRF middleware for all unit tests by patching `config.settings.csrf_enabled = False`.

Business endpoint tests mock `WebBackendClient` directly:

```python
@pytest.fixture
def mock_backend():
    return AsyncMock(spec=WebBackendClient)

def test_list_keys(client, mock_backend, mock_current_user):
    app.dependency_overrides[get_backend_client] = lambda: mock_backend
    mock_backend.list_keys.return_value = [{"email": "user@vpn.ru", "client_id": "abc"}]

    response = client.get("/api/v1/keys/")
    assert response.status_code == 200

    app.dependency_overrides.clear()
```

**Web E2E** (`web/tests_e2e/conftest.py`):

Playwright fixtures use the sync API. The `browser` fixture is session-scoped (Chromium, headless). Per-test fixtures create isolated browser contexts at 1280×720 (desktop) or 375×812 (mobile). Database fixtures (`registered_user`, `admin_user`, `user_with_tg_link`) set up and tear down PostgreSQL rows via `psql` subprocess calls.

The web E2E config is in `web/tests_e2e/config.py` and reads `BASE_URL`, `TEST_USER_EMAIL`, `TEST_USER_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `TEST_TG_ID` from the environment.

## Coverage Requirements

No coverage thresholds are configured in any `pytest.ini` or coverage config file. The bot component has `pytest-cov` and `coverage` installed (coverage == 7.13.0, pytest-cov == 7.0.0), enabling coverage reporting with `pytest --cov`, but no minimum threshold is enforced automatically.

## CI Integration

No CI/CD pipeline is configured in this repository (no `.github/workflows/` directory exists). Tests must be run manually per the commands above.

<!-- VERIFY: CI pipeline configuration if one is added in the future -->
