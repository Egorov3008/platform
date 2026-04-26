"""
Конфигурация Playwright fixtures для E2E тестов VPN Web Frontend. (Sync API)
"""
import pytest
import os
import subprocess
import bcrypt
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from tests_e2e.config import (
    BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD,
    TEST_USER_2_EMAIL, TEST_USER_2_PASSWORD,
    ADMIN_EMAIL, ADMIN_PASSWORD, TEST_TG_ID,
)

# ============================================================================
# Database helpers via subprocess (psql)
# ============================================================================

def _get_db_url():
    return os.getenv("DATABASE_URL", "postgresql://egorov:HG8ntEEVDI7Oh%2FRs@localhost:5432/vpn_bot")

def _run_sql(sql: str):
    """Выполняет SQL через psql."""
    env = os.environ.copy()
    env["DATABASE_URL"] = _get_db_url()
    result = subprocess.run(
        ["psql", _get_db_url(), "-c", sql],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and "already exists" not in result.stderr and "does not exist" not in result.stderr:
        print(f"SQL error: {result.stderr}")

def _clean_database():
    """Очищает тестовые данные."""
    _run_sql("DELETE FROM payments WHERE email LIKE 'test-e2e%' OR email LIKE 'admin-e2e%';")
    _run_sql("DELETE FROM keys WHERE client_id IN (SELECT client_id FROM web_users WHERE email LIKE 'test-e2e%' OR email LIKE 'admin-e2e%');")
    _run_sql("DELETE FROM magic_tokens;")
    _run_sql("DELETE FROM web_users WHERE email LIKE 'test-e2e%' OR email LIKE 'admin-e2e%';")
    _run_sql("DELETE FROM users WHERE tg_id::text LIKE '999%' OR tg_id::text LIKE '888%';")

def _create_user(email, password, role='user', tg_id=None):
    """Создает пользователя."""
    import datetime
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = datetime.datetime.utcnow().isoformat()
    
    if tg_id:
        _run_sql(f"INSERT INTO users (tg_id, username, first_name) VALUES ({tg_id}, 'user_{tg_id}', 'Test User') ON CONFLICT DO NOTHING;")
        _run_sql(f"INSERT INTO web_users (email, password_hash, tg_id) VALUES ('{email}', '{hashed}', {tg_id}) ON CONFLICT (email) DO NOTHING;")
    else:
        _run_sql(f"INSERT INTO web_users (email, password_hash) VALUES ('{email}', '{hashed}') ON CONFLICT (email) DO NOTHING;")

def _delete_user(email, tg_id=None):
    """Удаляет пользователя."""
    _run_sql(f"DELETE FROM keys WHERE client_id IN (SELECT client_id FROM web_users WHERE email = '{email}');")
    _run_sql(f"DELETE FROM web_users WHERE email = '{email}';")
    if tg_id:
        _run_sql(f"DELETE FROM users WHERE tg_id = {tg_id};")

# ============================================================================
# Database fixtures
# ============================================================================

@pytest.fixture
def db():
    """Фикстура для прямого доступа к БД."""
    return {"clean": _clean_database, "create_user": _create_user, "delete_user": _delete_user}


@pytest.fixture
def clean_database(db):
    """Очищает тестовые данные перед каждым тестом."""
    db["clean"]()
    yield


@pytest.fixture
def registered_user(db):
    """Создает зарегистрированного пользователя."""
    db["clean"]()
    _create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
    yield {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    _delete_user(TEST_USER_EMAIL)


@pytest.fixture
def admin_user(db):
    """Создает пользователя-администратора."""
    db["clean"]()
    _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, role='admin')
    yield {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    _delete_user(ADMIN_EMAIL)


@pytest.fixture
def user_with_tg_link(db):
    """Создает пользователя с привязанным Telegram."""
    db["clean"]()
    _create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD, tg_id=TEST_TG_ID)
    yield {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "tg_id": TEST_TG_ID}
    _delete_user(TEST_USER_EMAIL, TEST_TG_ID)

# ============================================================================
# Browser fixtures
# ============================================================================

@pytest.fixture(scope="session")
def browser():
    """Создает экземпляр браузера Chromium на всю сессию."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def context(browser: Browser):
    """Создает изолированный контекст браузера."""
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext):
    """Создает страницу."""
    p = context.new_page()
    p.set_default_timeout(10000)
    yield p


@pytest.fixture
def mobile_context(browser: Browser):
    """Контекст с мобильным viewport."""
    ctx = browser.new_context(
        viewport={"width": 375, "height": 812},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        user_agent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    )
    yield ctx
    ctx.close()


@pytest.fixture
def mobile_page(mobile_context: BrowserContext):
    """Страница с мобильным viewport."""
    p = mobile_context.new_page()
    p.set_default_timeout(10000)
    yield p

# ============================================================================
# Authentication fixtures
# ============================================================================

@pytest.fixture
def logged_in_user(page: Page, registered_user):
    """Авторизованный обычный пользователь."""
    page.goto(f"{BASE_URL}/#/login")
    page.wait_for_timeout(500)
    page.fill("#loginEmail", registered_user["email"])
    page.fill("#loginPassword", registered_user["password"])
    page.click("button[type='submit']")
    page.wait_for_timeout(2000)
    yield page


@pytest.fixture
def logged_in_admin(page: Page, admin_user):
    """Авторизованный администратор."""
    page.goto(f"{BASE_URL}/#/login")
    page.wait_for_timeout(500)
    page.fill("#loginEmail", admin_user["email"])
    page.fill("#loginPassword", admin_user["password"])
    page.click("button[type='submit']")
    page.wait_for_timeout(2000)
    yield page


@pytest.fixture
def logged_in_user_with_tg(page: Page, user_with_tg_link):
    """Авторизованный пользователь с привязанным Telegram."""
    page.goto(f"{BASE_URL}/#/login")
    page.wait_for_timeout(500)
    page.fill("#loginEmail", user_with_tg_link["email"])
    page.fill("#loginPassword", user_with_tg_link["password"])
    page.click("button[type='submit']")
    page.wait_for_timeout(2000)
    yield page
