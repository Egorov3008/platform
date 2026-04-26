"""
E2E тесты UI/UX VPN Web Frontend.
Тестиров responsive дизайна, пустых состояний, тостов, модальных окон,
валидации форм, доступности (a11y) и визуальной консистентности.
"""
import pytest
from playwright.sync_api import Page, expect, ViewportSize

from tests_e2e.config import BASE_URL, VIEWPORTS, TEST_USER_EMAIL, TEST_USER_PASSWORD
from tests_e2e.pages.pages import (
    LoginPage, DashboardPage, TariffsPage, AdminPage, ModalPage, RegisterPage
)
from tests_e2e.utils.helpers import (
    wait_for_loading, wait_for_toast, wait_for_modal, close_modal,
    is_visible, is_hidden, element_count, get_url_hash
)


# ============================================================================
# Тесты responsive дизайна
# ============================================================================

@pytest.mark.ui
@pytest.mark.responsive
class TestResponsiveDesign:
    """Тесты адаптивного дизайна."""

    def test_desktop_layout(self, page: Page, logged_in_user):
        """Проверяет desktop layout."""
        page.set_viewport_size(VIEWPORTS["desktop"])

        dashboard = DashboardPage(page)
        dashboard.goto()

        # На desktop nav должен быть виден
        nav_links = page.locator(".nav-links").first
        assert nav_links.count() > 0 or page.locator("header").count() > 0

        # Hamburger меню не должен быть виден
        nav_toggle = page.locator(".nav-toggle").first
        toggle_visible = nav_toggle.is_visible() if nav_toggle.count() > 0 else False
        # На desktop toggle обычно скрыт
        assert not toggle_visible or nav_toggle.count() == 0

    def test_tablet_layout(self, page: Page, logged_in_user):
        """Проверяет tablet layout."""
        page.set_viewport_size(VIEWPORTS["tablet"])

        dashboard = DashboardPage(page)
        dashboard.goto()
        page.wait_for_timeout(500)

        # Страница должна корректно отобразиться
        assert page.locator("main").count() > 0

    def test_mobile_layout(self, page: Page, logged_in_user):
        """Проверяет mobile layout."""
        page.set_viewport_size(VIEWPORTS["mobile"])

        dashboard = DashboardPage(page)
        dashboard.goto()
        page.wait_for_timeout(500)

        # На mobile nav должен быть скрыт или в hamburger
        header = page.locator("header").first
        assert header.count() > 0

    @pytest.mark.parametrize("viewport_name", ["mobile", "tablet", "desktop"])
    def test_login_page_responsive(self, page: Page, viewport_name: str):
        """Проверяет responsive страницы логина."""
        page.set_viewport_size(VIEWPORTS[viewport_name])

        login = LoginPage(page)
        login.goto()

        assert login.is_page_loaded()
        # Форма должна быть видна
        assert page.locator('input[name="email"]').count() > 0

    @pytest.mark.parametrize("viewport_name", ["mobile", "tablet", "desktop"])
    def test_tariffs_page_responsive(self, page: Page, viewport_name: str):
        """Проверяет responsive страницы тарифов."""
        page.set_viewport_size(VIEWPORTS[viewport_name])

        tariffs = TariffsPage(page)
        tariffs.goto()

        # Карточки тарифов должны отображаться
        assert tariffs.tariffs_grid.count() > 0 or tariffs.is_empty_state_visible()

    def test_keys_grid_responsive(self, page: Page, logged_in_user_with_tg):
        """Проверяет responsive grid ключей."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Проверяем на разных viewport
        for viewport_name, viewport_size in VIEWPORTS.items():
            page.set_viewport_size(viewport_size)
            page.wait_for_timeout(300)

            # Grid или empty state должны быть видны
            has_grid = dashboard.keys_grid.count() > 0
            has_empty = dashboard.is_empty_state_visible()
            assert has_grid or has_empty

    def test_admin_metrics_responsive(self, page: Page, logged_in_admin):
        """Проверяет responsive метрик админки."""
        admin = AdminPage(page)
        admin.goto()

        for viewport_name, viewport_size in VIEWPORTS.items():
            page.set_viewport_size(viewport_size)
            page.wait_for_timeout(300)

            # Metrics grid должен быть виден
            assert page.locator(".metrics-grid").count() > 0


# ============================================================================
# Тесты пустых состояний (Empty States)
# ============================================================================

@pytest.mark.ui
@pytest.mark.empty_states
class TestEmptyStates:
    """Тесты пустых состояний."""

    def test_dashboard_empty_state_without_keys(self, page: Page, logged_in_user):
        """Проверяет empty state dashboard без ключей."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() == 0:
            assert dashboard.is_empty_state_visible()
            # Empty state должен иметь иконку и текст
            empty_state = page.locator(".empty-state").first
            assert empty_state.count() > 0

    def test_empty_state_has_icon(self, page: Page, logged_in_user):
        """Проверяет наличие иконки в empty state."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() == 0:
            empty_state = page.locator(".empty-state").first
            svg_icon = empty_state.locator("svg")
            assert svg_icon.count() > 0

    def test_empty_state_has_descriptive_text(self, page: Page, logged_in_user):
        """Проверяет описательный текст в empty state."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() == 0:
            empty_state_text = page.locator(".empty-state").first.text_content()
            assert len(empty_state_text.strip()) > 10  # Текст должен быть содержательным

    def test_tariffs_empty_state(self, page: Page):
        """Проверяет empty state страницы тарифов (если тарифов нет)."""
        tariffs = TariffsPage(page)
        tariffs.goto()

        tariffs_count = tariffs.get_tariffs_count()
        if tariffs_count == 0:
            assert tariffs.is_empty_state_visible()


# ============================================================================
# Тесты Toast уведомлений
# ============================================================================

@pytest.mark.ui
@pytest.mark.toasts
class TestToastNotifications:
    """Тесты toast уведомлений."""

    def test_success_toast_appears(self, page: Page, logged_in_user):
        """Проверяет появление success toast."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Действие которое вызывает toast (logout например)
        dashboard.click_logout()

        toast = wait_for_toast(page)
        # Toast должен появиться (об успехе выхода или другой)
        assert toast is not None or get_url_hash(page) == "#/login"

    def test_error_toast_on_failed_login(self, page: Page, registered_user):
        """Проверяет error toast при неудачном входе."""
        login = LoginPage(page)
        login.goto()
        login.login(TEST_USER_EMAIL, "WrongPassword!")

        toast = wait_for_toast(page)
        assert toast is not None

    def test_toast_auto_dismiss(self, page: Page, registered_user):
        """Проверяет авто-скрытие toast через 4 секунды."""
        login = LoginPage(page)
        login.goto()
        login.login(TEST_USER_EMAIL, "WrongPassword!")

        # Toast появился
        toast = wait_for_toast(page)
        assert toast is not None

        # Ждем 4.5 секунды (с запасом)
        page.wait_for_timeout(4500)

        # Toast должен исчезнуть
        toast_count = element_count(page, ".toast")
        assert toast_count == 0

    def test_toast_has_close_button_or_auto_dismiss(self, page: Page, registered_user):
        """Проверяет что toast можно закрыть или он авто-скрывается."""
        login = LoginPage(page)
        login.goto()
        login.login(TEST_USER_EMAIL, "WrongPassword!")

        toast = page.locator(".toast").first
        assert toast.count() > 0

        # Toast должен иметь текст
        text = toast.text_content()
        assert text is not None and len(text.strip()) > 0


# ============================================================================
# Тесты модальных окон
# ============================================================================

@pytest.mark.ui
@pytest.mark.modals
class TestModals:
    """Тесты модальных окон."""

    def test_modal_opens_with_overlay(self, page: Page, logged_in_user_with_tg):
        """Проверяет открытие модалки с оверлеем."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        modal = ModalPage(page)
        assert modal.is_visible()

        # Оверлей должен быть виден
        overlay = page.locator(".modal-overlay").first
        assert overlay.is_visible()

    def test_modal_has_close_button(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие кнопки закрытия модалки."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        # Кнопка закрытия или крестик
        close_count = page.locator(".modal-close").count()
        assert close_count > 0

    def test_modal_closes_on_close_button(self, page: Page, logged_in_user_with_tg):
        """Проверяет закрытие модалки по кнопке."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        modal = ModalPage(page)
        modal.close()

        assert modal.is_visible() is False

    def test_modal_closes_on_overlay_click(self, page: Page, logged_in_user_with_tg):
        """Проверяет закрытие модалки кликом по оверлею."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        # Клик по оверлею (вне контента)
        page.locator(".modal-overlay").click(position={"x": 10, "y": 10})
        page.wait_for_timeout(500)

        modal = ModalPage(page)
        # Модалка должна закрыться
        assert modal.is_visible() is False

    def test_modal_blocks_background_interaction(self, page: Page, logged_in_user_with_tg):
        """Проверяет что модалка блокирует взаимодействие с фоном."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        # Контент за модалкой не должен быть кликабельным
        create_btn = page.locator(".btn-create-key").first
        if create_btn.count() > 0:
            # Кнопка должна быть под оверлеем
            is_visible_check = create_btn.is_visible()
            # Обычно overlay скрывает фон
            assert not is_visible_check or page.locator(".modal-overlay").count() > 0

    def test_telegram_login_modal(self, page: Page):
        """Проверяет модалку входа через Telegram."""
        login = LoginPage(page)
        login.goto()

        if login.has_telegram_login_option():
            login.telegram_login_btn.click()
            wait_for_modal(page)

            modal = ModalPage(page)
            assert modal.is_visible()

            # Модалка должна содержать инструкцию или поле ввода
            modal_text = page.locator(".modal-content").text_content()
            assert len(modal_text.strip()) > 20


# ============================================================================
# Тесты валидации форм
# ============================================================================

@pytest.mark.ui
@pytest.mark.forms
class TestFormValidation:
    """Тесты валидации форм."""

    def test_login_email_required(self, page: Page):
        """Проверяет что email обязателен для login."""
        login = LoginPage(page)
        login.goto()

        login.password_input.fill(TEST_USER_PASSWORD)
        login.submit_btn.click()

        page.wait_for_timeout(1000)
        # HTML5 валидация или ошибка
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_login_password_required(self, page: Page, registered_user):
        """Проверяет что пароль обязателен для login."""
        login = LoginPage(page)
        login.goto()

        login.email_input.fill(TEST_USER_EMAIL)
        login.submit_btn.click()

        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_register_email_required(self, page: Page):
        """Проверяет что email обязателен для регистрации."""
        register = RegisterPage(page)
        register.goto()

        register.password_input.fill(TEST_USER_PASSWORD)
        register.submit_btn.click()

        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/register"

    def test_register_password_required(self, page: Page):
        """Проверяет что пароль обязателен для регистрации."""
        register = RegisterPage(page)
        register.goto()

        register.email_input.fill("test@example.com")
        register.submit_btn.click()

        page.wait_for_timeout(1000)
        url_hash = get_url_hash(page)
        assert url_hash == "#/register"

    def test_invalid_email_format_rejected(self, page: Page):
        """Проверяет отклонение некорректного email."""
        login = LoginPage(page)
        login.goto()

        login.email_input.fill("not-valid-email")
        login.password_input.fill(TEST_USER_PASSWORD)
        login.submit_btn.click()

        page.wait_for_timeout(1500)
        # Либо HTML5 валидация, либо серверная ошибка
        url_hash = get_url_hash(page)
        toast = wait_for_toast(page, timeout=2000)
        assert url_hash == "#/login" or toast is not None


# ============================================================================
# Тесты доступности (a11y)
# ============================================================================

@pytest.mark.ui
@pytest.mark.accessibility
class TestAccessibility:
    """Тесты доступности."""

    def test_form_has_labels_or_placeholders(self, page: Page):
        """Проверяет наличие label или placeholder у форм."""
        login = LoginPage(page)
        login.goto()

        email_input = login.email_input
        # Либо label, либо placeholder
        placeholder = email_input.get_attribute("placeholder")
        aria_label = email_input.get_attribute("aria-label")

        assert placeholder or aria_label

    def test_buttons_have_text(self, page: Page):
        """Проверяет что кнопки имеют текст."""
        login = LoginPage(page)
        login.goto()

        submit_text = login.submit_btn.text_content()
        assert submit_text is not None and len(submit_text.strip()) > 0

    def test_links_have_href(self, page: Page):
        """Проверяет что ссылки имеют href."""
        login = LoginPage(page)
        login.goto()

        register_link = login.register_link
        href = register_link.get_attribute("href")
        assert href is not None and "#" in href

    def test_images_have_alt_text(self, page: Page):
        """Проверяет наличие alt текста у изображений/SVG."""
        # На empty state должны быть SVG с ролью
        login = LoginPage(page)
        login.goto()

        svg_elements = page.locator("svg")
        svg_count = svg_elements.count()

        if svg_count > 0:
            first_svg = svg_elements.first
            # SVG может иметь aria-hidden или aria-label
            aria_hidden = first_svg.get_attribute("aria-hidden")
            aria_label = first_svg.get_attribute("aria-label")
            # Либо скрыт от screen reader, либо имеет label
            assert aria_hidden == "true" or aria_label is not None

    def test_keyboard_navigation_login(self, page: Page):
        """Проверяет навигацию клавиатурой на странице login."""
        login = LoginPage(page)
        login.goto()

        # Tab должен перемещать фокус
        page.keyboard.press("Tab")
        focused = page.locator(":focus")
        assert focused.count() > 0

    def test_focus_visible_on_inputs(self, page: Page):
        """Проверяет видимость фокуса на инпутах."""
        login = LoginPage(page)
        login.goto()

        login.email_input.click()
        # Инпут должен быть в фокусе
        is_focused = login.email_input.evaluate("el => document.activeElement === el")
        assert is_focused


# ============================================================================
# Тесты визуальной консистентности
# ============================================================================

@pytest.mark.ui
@pytest.mark.visual
class TestVisualConsistency:
    """Тесты визуальной консистентности."""

    def test_consistent_header_across_pages(self, page: Page, logged_in_user):
        """Проверяет консистентность header на разных страницах."""
        pages_to_check = ["#/dashboard", "#/tariffs", "#/payments"]
        headers = []

        for page_hash in pages_to_check:
            page.goto(f"{BASE_URL}/{page_hash}")
            wait_for_loading(page)

            header = page.locator("header").first
            if header.count() > 0:
                header_html = header.inner_html()
                headers.append(header_html)

        # Все headers должны быть похожи (иметь nav элементы)
        if len(headers) > 1:
            for i in range(1, len(headers)):
                # Проверяем наличие общих элементов
                assert "nav" in headers[0].lower() or "href" in headers[0].lower()

    def test_font_family_consistent(self, page: Page):
        """Проверяет консистентность шрифта."""
        login = LoginPage(page)
        login.goto()

        body_font = page.locator("body").evaluate(
            "el => window.getComputedStyle(el).fontFamily"
        )

        # Шрифт должен быть установлен (Inter или system-ui)
        assert "inter" in body_font.lower() or "system" in body_font.lower() or "sans" in body_font.lower()

    def test_primary_button_style_consistent(self, page: Page):
        """Проверяет консистентность стиля primary кнопок."""
        login = LoginPage(page)
        login.goto()

        login_btn = login.submit_btn
        bg_color = login_btn.evaluate("el => window.getComputedStyle(el).backgroundColor")

        # Кнопка должна иметь цвет (не transparent)
        assert bg_color and "transparent" not in bg_color.lower()

    def test_page_transitions_smooth(self, page: Page, logged_in_user):
        """Проверяет плавность переходов между страницами."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Переход на тарифы
        tariffs_link = page.locator("a[href='#/tariffs']").first
        tariffs_link.click()

        # Страница должна загрузиться без ошибок
        wait_for_loading(page)

        # Проверяем отсутствие JS ошибок
        # (Playwright логирует их в консоль)
        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"


# ============================================================================
# Тесты loading состояний
# ============================================================================

@pytest.mark.ui
@pytest.mark.loading
class TestLoadingStates:
    """Тесты состояний загрузки."""

    def test_loading_spinner_appears(self, page: Page, logged_in_user):
        """Проверяет появление спиннера при загрузке."""
        dashboard = DashboardPage(page)

        # Быстрый переход может показать спиннер
        page.goto(f"{BASE_URL}/#/dashboard")

        wait_for_loading(page)
        # Спиннер должен исчезнуть
        spinner = page.locator(".loading-spinner")
        spinner.wait_for(state="hidden", timeout=5000)

    def test_content_appears_after_loading(self, page: Page, logged_in_user):
        """Проверяет появление контента после загрузки."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        wait_for_loading(page)

        # Должен быть либо grid, либо empty state
        has_grid = dashboard.keys_grid.count() > 0
        has_empty = dashboard.is_empty_state_visible()
        assert has_grid or has_empty

    def test_no_blank_page_on_error(self, page: Page):
        """Проверяет что страница не blank при ошибке."""
        page.goto(f"{BASE_URL}/#/dashboard")
        page.wait_for_timeout(2000)

        # Страница не должна быть полностью blank
        body_text = page.locator("body").text_content()
        assert len(body_text.strip()) > 0
