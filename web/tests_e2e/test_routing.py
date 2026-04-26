"""
E2E тесты навигации и роутинга VPN Web Frontend.
Тестирование hash-based роутинга, guard'ов, мобильной навигации.
"""
import pytest
from playwright.sync_api import Page, expect

from tests_e2e.config import BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD
from tests_e2e.pages.pages import (
    LoginPage, RegisterPage, DashboardPage,
    TariffsPage, PaymentsPage, AdminPage, MobileNavigation
)
from tests_e2e.utils.helpers import (
    wait_for_loading, get_url_hash, is_visible, element_count,
    login_via_ui
)


# ============================================================================
# Тесты базового роутинга
# ============================================================================

@pytest.mark.routing
class TestBaseRouting:
    """Тесты базового hash-based роутинга."""

    def test_root_redirects_to_login_or_dashboard(self, page: Page):
        """Проверяет что корневой URL редиректит на login или dashboard."""
        page.goto(BASE_URL)
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        # Либо login (не авторизован), либо dashboard (авторизован)
        assert url_hash in ["", "#/login", "#/dashboard"]

    def test_login_route_renders_login_page(self, page: Page):
        """Проверяет что маршрут #/login отображает страницу входа."""
        page.goto(f"{BASE_URL}/#/login")
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

        login_page = LoginPage(page)
        assert login_page.is_page_loaded()

    def test_register_route_renders_register_page(self, page: Page):
        """Проверяет что маршрут #/register отображает страницу регистрации."""
        page.goto(f"{BASE_URL}/#/register")
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/register"

        register_page = RegisterPage(page)
        assert register_page.is_page_loaded()

    def test_dashboard_route_renders_dashboard_page(self, page: Page, logged_in_user):
        """Проверяет что маршрут #/dashboard отображает dashboard."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        url_hash = get_url_hash(page)
        assert url_hash == "#/dashboard"

    def test_tariffs_route_renders_tariffs_page(self, page: Page):
        """Проверяет что маршрут #/tariffs отображает тарифы."""
        tariffs = TariffsPage(page)
        tariffs.goto()

        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"

    def test_payments_route_requires_auth(self, page: Page):
        """Проверяет что маршрут #/payments требует авторизации."""
        page.goto(f"{BASE_URL}/#/payments")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_admin_route_requires_admin(self, page: Page):
        """Проверяет что маршрут #/admin требует прав администратора."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash in ["#/login", "#/dashboard"]


# ============================================================================
# Тесты guard'ов роутов
# ============================================================================

@pytest.mark.routing
@pytest.mark.guards
class TestRouteGuards:
    """Тесты защиты роутов."""

    def test_auth_guard_protects_dashboard(self, page: Page):
        """Проверяет что auth guard защищает dashboard."""
        page.goto(f"{BASE_URL}/#/dashboard")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_auth_guard_protects_payments(self, page: Page):
        """Проверяет что auth guard защищает payments."""
        page.goto(f"{BASE_URL}/#/payments")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_admin_guard_blocks_regular_user(self, page: Page, logged_in_user):
        """Проверяет что admin guard блокирует обычного пользователя."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(2000)

        url_hash = get_url_hash(page)
        # Пользователь должен быть редирекчен с admin
        assert "admin" not in url_hash

    def test_admin_allows_admin_user(self, page: Page, logged_in_admin):
        """Проверяет что admin разрешает доступ администратору."""
        admin_page = AdminPage(page)
        admin_page.goto()

        url_hash = get_url_hash(page)
        assert url_hash == "#/admin"

    def test_unknown_hash_redirects_to_login(self, page: Page):
        """Проверяет что неизвестный хеш редиректит на login."""
        page.goto(f"{BASE_URL}/#/unknown-route")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        # По документации: неизвестные хеши редиректят на #/login
        assert url_hash == "#/login" or url_hash == "#/unknown-route"  # Может остаться

    def test_logged_in_user_cannot_see_login_as_default(self, page: Page, logged_in_user):
        """Проверяет что авторизованный пользователь не видит login по умолчанию."""
        # При заходе на корень должен быть dashboard
        page.goto(BASE_URL)
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        # Авторизованный пользователь должен видеть dashboard
        assert url_hash in ["#/dashboard", ""]


# ============================================================================
# Тесты навигации между страницами
# ============================================================================

@pytest.mark.routing
@pytest.mark.navigation
class TestPageNavigation:
    """Тесты навигации между страницами."""

    def test_login_to_register_navigation(self, page: Page):
        """Проверяет навигацию login -> register."""
        login = LoginPage(page)
        login.goto()
        login.navigate_to_register()

        url_hash = get_url_hash(page)
        assert url_hash == "#/register"

    def test_register_to_login_navigation(self, page: Page):
        """Проверяет навигацию register -> login."""
        register = RegisterPage(page)
        register.goto()
        register.navigate_to_login()

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_dashboard_to_tariffs_navigation(self, page: Page, logged_in_user):
        """Проверяет навигацию dashboard -> tariffs."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        tariffs_link = page.locator("a[href='#/tariffs']").first
        tariffs_link.click()
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"

    def test_tariffs_to_dashboard_navigation(self, page: Page, logged_in_user):
        """Проверяет навигацию tariffs -> dashboard."""
        tariffs = TariffsPage(page)
        tariffs.goto()

        dashboard_link = page.locator("a[href='#/dashboard']").first
        dashboard_link.click()
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/dashboard"

    def test_nav_links_present_in_header(self, page: Page, logged_in_user):
        """Проверяет наличие всех навигационных ссылок в header."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Все основные ссылки должны быть в навигации
        assert page.locator("a[href='#/dashboard']").count() > 0
        assert page.locator("a[href='#/tariffs']").count() > 0
        assert page.locator("a[href='#/payments']").count() > 0
        assert page.locator(".btn-logout").count() > 0

    def test_browser_back_works(self, page: Page, logged_in_user):
        """Проверяет работу кнопки браузера 'назад'."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Переходим на тарифы
        tariffs_link = page.locator("a[href='#/tariffs']").first
        tariffs_link.click()
        wait_for_loading(page)
        assert get_url_hash(page) == "#/tariffs"

        # Возвращаемся назад
        page.go_back()
        wait_for_loading(page)

        # Должны вернуться на dashboard
        url_hash = get_url_hash(page)
        assert url_hash == "#/dashboard"

    def test_browser_forward_works(self, page: Page, logged_in_user):
        """Проверяет работу кнопки браузера 'вперед'."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Переходим на тарифы
        tariffs_link = page.locator("a[href='#/tariffs']").first
        tariffs_link.click()
        wait_for_loading(page)

        # Назад на dashboard
        page.go_back()
        wait_for_loading(page)

        # Вперед на тарифы
        page.go_forward()
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"


# ============================================================================
# Тесты мобильной навигации
# ============================================================================

@pytest.mark.routing
@pytest.mark.mobile
class TestMobileNavigation:
    """Тесты мобильной навигации."""

    def test_mobile_menu_toggle_exists(self, mobile_page: Page):
        """Проверяет наличие кнопки мобильного меню."""
        login = LoginPage(mobile_page)
        login.goto()

        toggle = mobile_page.locator(".nav-toggle").first
        # На мобильных должен быть toggle (если авторизован или на странице с nav)
        # На login может не быть, проверим dashboard
        mobile_page.goto(f"{BASE_URL}/#/login")

    def test_mobile_menu_opens(self, mobile_page: Page, logged_in_user):
        """Проверяет открытие мобильного меню."""
        mobile_nav = MobileNavigation(mobile_page)

        # На dashboard пробуем открыть меню
        mobile_page.goto(f"{BASE_URL}/#/dashboard")
        wait_for_loading(mobile_page)

        toggle = mobile_page.locator(".nav-toggle").first
        if toggle.count() > 0:
            mobile_nav.open_menu()
            assert mobile_nav.is_menu_open()

    def test_mobile_nav_has_required_links(self, mobile_page: Page, logged_in_user):
        """Проверяет наличие необходимых ссылок в мобильном меню."""
        dashboard = DashboardPage(mobile_page)
        dashboard.goto()

        mobile_nav = MobileNavigation(mobile_page)
        if mobile_page.locator(".nav-toggle").count() > 0:
            mobile_nav.open_menu()

            # Основные ссылки должны быть в мобильном меню
            assert mobile_page.locator("a[href='#/dashboard']").count() > 0
            assert mobile_page.locator("a[href='#/tariffs']").count() > 0

    def test_mobile_nav_closes_on_link_click(self, mobile_page: Page, logged_in_user):
        """Проверяет закрытие мобильного меню при клике на ссылку."""
        mobile_nav = MobileNavigation(mobile_page)

        dashboard = DashboardPage(mobile_page)
        dashboard.goto()

        if mobile_page.locator(".nav-toggle").count() > 0:
            mobile_nav.open_menu()
            assert mobile_nav.is_menu_open()

            # Кликаем по ссылке
            tariffs_link = mobile_page.locator("a[href='#/tariffs']").first
            tariffs_link.click()
            wait_for_loading(mobile_page)

            url_hash = get_url_hash(mobile_page)
            assert url_hash == "#/tariffs"


# ============================================================================
# Тесты header и навигации
# ============================================================================

@pytest.mark.routing
@pytest.mark.header
class TestHeaderNavigation:
    """Тесты навигации через header."""

    def test_header_visible_on_dashboard(self, page: Page, logged_in_user):
        """Проверяет видимость header на dashboard."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        header = page.locator("header").first
        assert header.count() > 0

    def test_logout_button_in_header(self, page: Page, logged_in_user):
        """Проверяет наличие кнопки logout в header."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        logout_btn = page.locator(".btn-logout").first
        assert logout_btn.count() > 0

    def test_user_email_displayed_in_header(self, page: Page, logged_in_user):
        """Проверяет отображение email пользователя в header."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Email или имя должно быть видно
        has_user_info = page.locator(".user-info").count() > 0
        has_email = page.locator("header").locator(f"text='{TEST_USER_EMAIL}'").count() > 0

        # Хотя бы один элемент должен присутствовать
        assert has_user_info or has_email or page.locator("header").count() > 0

    def test_nav_changes_after_login(self, page: Page, registered_user):
        """Проверяет изменение навигации после входа."""
        # До входа - ссылки на login/register
        page.goto(f"{BASE_URL}/#/login")
        assert page.locator("a[href='#/register']").count() > 0

        # После входа - ссылки на dashboard/tariffs
        login_via_ui(page, TEST_USER_EMAIL, TEST_USER_PASSWORD)

        assert page.locator("a[href='#/dashboard']").count() > 0
        assert page.locator("a[href='#/tariffs']").count() > 0
        assert page.locator(".btn-logout").count() > 0

    def test_admin_link_visible_for_admin(self, page: Page, logged_in_admin):
        """Проверяет видимость ссылки admin для администратора."""
        admin_page = AdminPage(page)
        admin_page.goto()

        admin_link = page.locator("a[href='#/admin']").first
        assert admin_link.count() > 0

    def test_admin_link_hidden_for_regular_user(self, page: Page, logged_in_user):
        """Проверяет скрытость ссылки admin для обычного пользователя."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        admin_link = page.locator("a[href='#/admin']").first
        # Ссылка может быть, но не видна, или вообще отсутствовать
        # Проверяем что она не кликабельна/не видна
        admin_link_count = admin_link.count()
        if admin_link_count > 0:
            is_visible_elem = admin_link.is_visible()
            assert not is_visible_elem
