"""
E2E тесты аутентификации VPN Web Frontend. (Sync API)
"""
import pytest
from playwright.sync_api import Page, expect

from tests_e2e.config import (
    BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD,
    TEST_USER_2_EMAIL, TEST_USER_2_PASSWORD, TEST_TG_ID,
)
from tests_e2e.pages.pages import LoginPage, RegisterPage, DashboardPage
from tests_e2e.utils.helpers import (
    login_via_ui, register_via_ui, get_access_token, get_refresh_token,
    clear_local_storage, get_url_hash, wait_for_toast, element_count
)


# ============================================================================
# Тесты страницы логина
# ============================================================================

@pytest.mark.auth
@pytest.mark.login
class TestLoginPage:
    """Тесты страницы входа."""
    
    def test_login_page_renders(self, page: Page):
        """Проверяет корректную отрисовку страницы логина."""
        login_page = LoginPage(page)
        login_page.goto()
        
        assert login_page.is_page_loaded()
        assert login_page.email_input.count() == 1
        assert login_page.password_input.count() == 1
        assert login_page.submit_btn.count() == 1
    
    def test_login_page_has_telegram_option(self, page: Page):
        """Проверяет наличие кнопки входа через Telegram."""
        login_page = LoginPage(page)
        login_page.goto()
        assert login_page.has_telegram_login_option()
    
    def test_login_page_has_register_link(self, page: Page):
        """Проверяет ссылку на регистрацию."""
        login_page = LoginPage(page)
        login_page.goto()
        assert login_page.register_link.count() == 1
        register_text = login_page.register_link.text_content()
        assert "егистраци" in register_text
    
    def test_login_navigates_to_register(self, page: Page):
        """Проверяет переход на страницу регистрации."""
        login_page = LoginPage(page)
        login_page.goto()
        login_page.navigate_to_register()
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/register"


@pytest.mark.auth
@pytest.mark.login
class TestLoginFunctionality:
    """Тесты функционала входа."""
    
    def test_successful_login(self, page: Page, registered_user):
        """Проверяет успешный вход с корректными данными."""
        login_page = LoginPage(page)
        login_page.goto()
        login_page.login(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/dashboard"
        
        token = get_access_token(page)
        assert token is not None
        assert len(token) > 10
    
    def test_failed_login_wrong_password(self, page: Page, registered_user):
        """Проверяет поведение при неверном пароле."""
        login_page = LoginPage(page)
        login_page.goto()
        login_page.login(TEST_USER_EMAIL, "WrongPassword123!")
        
        toast_msg = wait_for_toast(page)
        assert toast_msg is not None
        assert "неверн" in toast_msg.lower() or "ошибк" in toast_msg.lower() or "error" in toast_msg.lower()
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_failed_login_nonexistent_user(self, page: Page):
        """Проверяет поведение при входе несуществующего пользователя."""
        login_via_ui(page, "nonexistent@example.com", "SomePassword123!")
        
        toast_msg = wait_for_toast(page)
        assert toast_msg is not None
    
    def test_login_with_empty_email(self, page: Page):
        """Проверяет вход с пустым email."""
        login_page = LoginPage(page)
        login_page.goto()
        login_page.password_input.fill(TEST_USER_PASSWORD)
        login_page.submit_btn.click()
        
        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_login_with_empty_password(self, page: Page, registered_user):
        """Проверяет вход с пустым паролем."""
        login_page = LoginPage(page)
        login_page.goto()
        login_page.email_input.fill(TEST_USER_EMAIL)
        login_page.submit_btn.click()
        
        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_login_stores_tokens(self, page: Page, registered_user):
        """Проверяет сохранение JWT токенов в localStorage."""
        login_via_ui(page, TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        access_token = get_access_token(page)
        refresh_token = get_refresh_token(page)
        
        assert access_token is not None
        assert refresh_token is not None
        assert access_token.startswith("eyJ")
        assert refresh_token.startswith("eyJ")
    
    def test_login_preserves_url_hash_after_redirect(self, page: Page, registered_user):
        """Проверяет что после входа пользователь попадает на dashboard."""
        login_via_ui(page, TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert "#/dashboard" in page.url


# ============================================================================
# Тесты страницы регистрации
# ============================================================================

@pytest.mark.auth
@pytest.mark.register
class TestRegisterPage:
    """Тесты страницы регистрации."""
    
    def test_register_page_renders(self, page: Page):
        """Проверяет корректную отрисовку страницы регистрации."""
        register_page = RegisterPage(page)
        register_page.goto()
        
        assert register_page.is_page_loaded()
        assert register_page.email_input.count() == 1
        assert register_page.password_input.count() == 1
        assert register_page.submit_btn.count() == 1
    
    def test_register_has_optional_tg_field(self, page: Page):
        """Проверяет наличие опционального поля Telegram ID."""
        register_page = RegisterPage(page)
        register_page.goto()
        assert register_page.tg_id_input.count() == 1
    
    def test_register_navigates_to_login(self, page: Page):
        """Проверяет переход на страницу логина."""
        register_page = RegisterPage(page)
        register_page.goto()
        register_page.navigate_to_login()
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"


@pytest.mark.auth
@pytest.mark.register
class TestRegisterFunctionality:
    """Тесты функционала регистрации."""
    
    def test_successful_registration(self, page: Page, clean_database):
        """Проверяет успешную регистрацию нового пользователя."""
        register_page = RegisterPage(page)
        register_page.goto()
        register_page.register(TEST_USER_2_EMAIL, TEST_USER_2_PASSWORD)
        
        url_hash = get_url_hash(page)
        assert url_hash in ["#/dashboard", "#/login"]
    
    def test_registration_with_tg_id(self, page: Page, clean_database):
        """Проверяет регистрацию с указанием Telegram ID."""
        register_page = RegisterPage(page)
        register_page.goto()
        register_page.register(TEST_USER_2_EMAIL, TEST_USER_2_PASSWORD, tg_id="123456789")
        
        url_hash = get_url_hash(page)
        assert url_hash in ["#/dashboard", "#/login"]
    
    def test_duplicate_registration(self, page: Page, registered_user):
        """Проверяет регистрацию существующего пользователя."""
        register_page = RegisterPage(page)
        register_page.goto()
        register_page.register(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        toast_msg = wait_for_toast(page)
        assert toast_msg is not None
    
    def test_registration_invalid_email(self, page: Page, clean_database):
        """Проверяет регистрацию с некорректным email."""
        register_page = RegisterPage(page)
        register_page.goto()
        
        register_page.email_input.fill("not-an-email")
        register_page.password_input.fill(TEST_USER_2_PASSWORD)
        register_page.submit_btn.click()
        
        page.wait_for_timeout(1000)
        toast_msg = wait_for_toast(page, timeout=3000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/register" or toast_msg is not None
    
    def test_registration_short_password(self, page: Page, clean_database):
        """Проверяет регистрацию с коротким паролем."""
        register_page = RegisterPage(page)
        register_page.goto()
        register_page.email_input.fill(TEST_USER_2_EMAIL)
        register_page.password_input.fill("123")
        register_page.submit_btn.click()
        
        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/register"


# ============================================================================
# Тесты logout
# ============================================================================

@pytest.mark.auth
@pytest.mark.logout
class TestLogout:
    """Тесты выхода из системы."""
    
    def test_logout_clears_tokens(self, page: Page, logged_in_user):
        """Проверяет очистку токенов при выходе."""
        dashboard = DashboardPage(page)
        
        assert get_access_token(page) is not None
        
        dashboard.click_logout()
        page.wait_for_timeout(500)
        
        assert get_access_token(page) is None
    
    def test_logout_redirects_to_login(self, page: Page, logged_in_user):
        """Проверяет редирект на login после выхода."""
        dashboard = DashboardPage(page)
        dashboard.click_logout()
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_cannot_access_protected_route_after_logout(self, page: Page, logged_in_user):
        """Проверяет что после logout нельзя попасть на защищенную страницу."""
        dashboard = DashboardPage(page)
        dashboard.click_logout()
        
        dashboard.goto()
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"


# ============================================================================
# Тесты защищенных роутов
# ============================================================================

@pytest.mark.auth
@pytest.mark.routes
class TestProtectedRoutes:
    """Тесты защиты роутов."""
    
    def test_unauthenticated_redirected_from_dashboard(self, page: Page):
        """Проверяет редирект неавторизованного пользователя с dashboard."""
        page.goto(f"{BASE_URL}/#/dashboard")
        page.wait_for_timeout(1000)
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_unauthenticated_redirected_from_payments(self, page: Page):
        """Проверяет редирект неавторизованного пользователя с payments."""
        page.goto(f"{BASE_URL}/#/payments")
        page.wait_for_timeout(1000)
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_unauthenticated_redirected_from_admin(self, page: Page):
        """Проверяет редирект неавторизованного пользователя с admin."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(1000)
        
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"
    
    def test_regular_user_redirected_from_admin(self, page: Page, logged_in_user):
        """Проверяет что обычный пользователь редиректится с admin страницы."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(2000)
        
        url_hash = get_url_hash(page)
        assert "dashboard" in url_hash or url_hash == "#/dashboard"


# ============================================================================
# Тесты localStorage и токенов
# ============================================================================

@pytest.mark.auth
@pytest.mark.tokens
class TestTokenManagement:
    """Тесты управления токенами."""
    
    def test_tokens_are_jwt_format(self, page: Page, logged_in_user):
        """Проверяет что токены имеют формат JWT."""
        access_token = get_access_token(page)
        refresh_token = get_refresh_token(page)
        
        assert access_token.startswith("eyJ")
        assert refresh_token.startswith("eyJ")
    
    def test_no_tokens_before_login(self, page: Page):
        """Проверяет отсутствие токенов до входа."""
        page.goto(f"{BASE_URL}/#/login")
        page.wait_for_timeout(1000)
        
        assert get_access_token(page) is None
        assert get_refresh_token(page) is None
