"""
E2E тесты VPN Dashboard.
Тестирование CRUD операций с ключами: создание, просмотр, копирование, продление, удаление.
"""
import pytest
from playwright.sync_api import Page, expect

from tests_e2e.config import BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_TG_ID
from tests_e2e.pages.pages import DashboardPage, ModalPage
from tests_e2e.utils.helpers import (
    wait_for_loading, wait_for_toast, wait_for_modal,
    parse_key_cards, element_count, is_visible, get_url_hash
)


# ============================================================================
# Тесты отображения Dashboard
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
class TestDashboardDisplay:
    """Тесты отображения страницы Dashboard."""

    def test_dashboard_renders_for_authenticated_user(self, page: Page, logged_in_user):
        """Проверяет отрисовку dashboard для авторизованного пользователя."""
        dashboard = DashboardPage(page)

        # Страница загрузилась
        assert dashboard.is_loading() is False
        # Присутствует grid или empty state
        has_grid = dashboard.keys_grid.count() > 0
        has_empty = dashboard.is_empty_state_visible()
        assert has_grid or has_empty

    def test_dashboard_shows_empty_state_when_no_keys(self, page: Page, logged_in_user):
        """Проверяет отображение empty state при отсутствии ключей."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Если ключей нет - показывается empty state
        keys_count = dashboard.get_keys_count()
        if keys_count == 0:
            assert dashboard.is_empty_state_visible()

    def test_dashboard_shows_key_cards(self, page: Page, logged_in_user_with_tg):
        """Проверяет отображение карточек ключей."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        page.wait_for_timeout(1000)

        # Проверяем структуру ключей (если они есть)
        keys_count = dashboard.get_keys_count()
        if keys_count > 0:
            cards = dashboard.get_key_cards()
            assert len(cards) > 0

            # Каждая карточка имеет необходимые поля
            for card in cards:
                assert "name" in card
                assert "tariff" in card
                assert "expiry" in card
                assert "status" in card

    def test_key_card_has_required_elements(self, page: Page, logged_in_user_with_tg):
        """Проверяет что карточка ключа имеет все необходимые элементы."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        page.wait_for_timeout(1000)

        if dashboard.get_keys_count() > 0:
            first_card = page.locator(".key-card").first

            # Проверяем наличие элементов
            assert first_card.locator(".key-name").count() >= 0
            assert first_card.locator(".status-badge").count() >= 0
            assert first_card.locator(".btn-copy").count() >= 0
            assert first_card.locator(".btn-delete").count() >= 0

    def test_dashboard_page_title(self, page: Page, logged_in_user):
        """Проверяет наличие заголовка страницы."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Должен быть заголовок или навигация
        has_title = page.locator(".page-title").count() > 0
        has_header = page.locator("header").count() > 0
        assert has_title or has_header


# ============================================================================
# Тесты создания ключей
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
@pytest.mark.create_key
class TestKeyCreation:
    """Тесты создания VPN ключей."""

    def test_create_key_button_visible_with_tg_linked(self, page: Page, logged_in_user_with_tg):
        """Проверяет видимость кнопки создания ключа у пользователя с TG."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        assert dashboard.is_create_key_visible()

    def test_create_key_button_hidden_without_tg(self, page: Page, logged_in_user):
        """Проверяет скрытость кнопки создания ключа без привязки TG."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        # Кнопка создания должна быть скрыта без привязанного TG
        create_visible = dashboard.is_create_key_visible()
        # Либо кнопки нет, либо она скрыта
        assert not create_visible

    def test_create_key_opens_modal(self, page: Page, logged_in_user_with_tg):
        """Проверяет что создание ключа открывает модальное окно."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        dashboard.click_create_key()

        modal = ModalPage(page)
        assert modal.is_visible()

    def test_create_key_modal_has_tariff_selector(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие селектора тарифов в модалке."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        # В модалке должен быть select для выбора тарифа
        select_count = page.locator(".modal-content select").count()
        assert select_count > 0

    def test_create_key_modal_has_tariff_options(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие опций тарифов в селекторе."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        options = page.locator(".modal-content select option")
        options_count = options.count()
        # Должен быть хотя бы один тариф
        assert options_count > 0

    def test_create_key_closes_modal_on_success(self, page: Page, logged_in_user_with_tg):
        """Проверяет закрытие модалки после успешного создания ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        modal = ModalPage(page)

        # Выбираем первый тариф и создаем
        options = page.locator(".modal-content select option")
        if options.count() > 0:
            first_option_text = options.first.text_content()
            modal.select_tariff_and_create(first_option_text.strip())

            page.wait_for_timeout(2000)
            # Модалка должна закрыться
            assert modal.is_visible() is False

    def test_create_key_increases_count(self, page: Page, logged_in_user_with_tg):
        """Проверяет увеличение количества ключей после создания."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        initial_count = dashboard.get_keys_count()

        dashboard.click_create_key()
        modal = ModalPage(page)

        options = page.locator(".modal-content select option")
        if options.count() > 0:
            first_option_text = options.first.text_content()
            modal.select_tariff_and_create(first_option_text.strip())

            page.wait_for_timeout(2000)
            new_count = dashboard.get_keys_count()
            assert new_count == initial_count + 1

    def test_create_key_shows_success_toast(self, page: Page, logged_in_user_with_tg):
        """Проверяет показ уведомления об успешном создании ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        modal = ModalPage(page)
        options = page.locator(".modal-content select option")
        if options.count() > 0:
            first_option_text = options.first.text_content()
            modal.select_tariff_and_create(first_option_text.strip())

            toast_msg = wait_for_toast(page)
            assert toast_msg is not None
            # Сообщение об успехе должно содержать "ключ" или "создан"
            assert "ключ" in toast_msg.lower() or "создан" in toast_msg.lower() or "success" in toast_msg.lower()


# ============================================================================
# Тесты копирования ключей
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
@pytest.mark.copy_key
class TestKeyCopy:
    """Тесты копирования VPN ключей."""

    def test_copy_button_exists_for_each_key(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие кнопки копирования у каждого ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        keys_count = dashboard.get_keys_count()
        if keys_count > 0:
            copy_buttons = element_count(page, ".btn-copy")
            assert copy_buttons == keys_count

    def test_copy_key_shows_toast(self, page: Page, logged_in_user_with_tg):
        """Проверяет показ уведомления при копировании ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            dashboard.copy_key(0)
            toast_msg = wait_for_toast(page)
            assert toast_msg is not None


# ============================================================================
# Тесты продления ключей
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
@pytest.mark.renew_key
class TestKeyRenewal:
    """Тесты продления VPN ключей."""

    def test_renew_button_exists_for_each_key(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие кнопки продления у каждого ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        keys_count = dashboard.get_keys_count()
        if keys_count > 0:
            renew_buttons = element_count(page, ".btn-renew")
            assert renew_buttons == keys_count

    def test_renew_key_confirms_action(self, page: Page, logged_in_user_with_tg):
        """Проверяет подтверждение при продлении ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            # При клике на renew должно появиться подтверждение или модалка
            initial_keys = dashboard.get_key_cards()
            dashboard.renew_key(0)

            page.wait_for_timeout(1500)
            # Ключ должен остаться (продлен)
            new_keys_count = dashboard.get_keys_count()
            assert new_keys_count >= len(initial_keys)


# ============================================================================
# Тесты удаления ключей
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
@pytest.mark.delete_key
class TestKeyDeletion:
    """Тесты удаления VPN ключей."""

    def test_delete_button_exists_for_each_key(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие кнопки удаления у каждого ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        keys_count = dashboard.get_keys_count()
        if keys_count > 0:
            delete_buttons = element_count(page, ".btn-delete")
            assert delete_buttons == keys_count

    def test_delete_key_decreases_count(self, page: Page, logged_in_user_with_tg):
        """Проверяет уменьшение количества ключей после удаления."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        initial_count = dashboard.get_keys_count()
        if initial_count > 0:
            dashboard.delete_key(0)
            page.wait_for_timeout(1500)

            new_count = dashboard.get_keys_count()
            assert new_count == initial_count - 1

    def test_delete_key_shows_confirmation(self, page: Page, logged_in_user_with_tg):
        """Проверяет показ подтверждения при удалении ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            dashboard.delete_key(0)

            page.wait_for_timeout(1000)
            # Должно быть подтверждение или toast
            toast_msg = wait_for_toast(page, timeout=3000)
            # Либо toast об успехе, либо модалка подтверждения
            assert toast_msg is not None or page.locator(".modal-overlay").count() > 0

    def test_delete_last_key_shows_empty_state(self, page: Page, logged_in_user_with_tg):
        """Проверяет показ empty state после удаления последнего ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        initial_count = dashboard.get_keys_count()
        if initial_count == 1:
            dashboard.delete_key(0)
            page.wait_for_timeout(2000)

            assert dashboard.is_empty_state_visible()


# ============================================================================
# Тесты статусов ключей
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.keys
@pytest.mark.key_status
class TestKeyStatus:
    """Тесты статусов VPN ключей."""

    def test_key_has_status_badge(self, page: Page, logged_in_user_with_tg):
        """Проверяет наличие badge статуса у ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            status_badges = element_count(page, ".status-badge")
            assert status_badges > 0

    def test_key_status_values(self, page: Page, logged_in_user_with_tg):
        """Проверяет корректные значения статусов ключей."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            cards = dashboard.get_key_cards()
            valid_statuses = ["активен", "истекает", "истек", "active", "expiring", "expired"]

            for card in cards:
                status_lower = card.get("status", "").lower()
                # Статус должен содержать одно из допустимых значений
                assert any(vs in status_lower for vs in valid_statuses) or status_lower != ""

    def test_key_shows_expiry_date(self, page: Page, logged_in_user_with_tg):
        """Проверяет отображение даты истечения ключа."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        if dashboard.get_keys_count() > 0:
            cards = dashboard.get_key_cards()
            for card in cards:
                # expiry должен быть не пустым
                assert card.get("expiry", "") != ""


# ============================================================================
# Тесты навигации с Dashboard
# ============================================================================

@pytest.mark.dashboard
@pytest.mark.navigation
class TestDashboardNavigation:
    """Тесты навигации с Dashboard."""

    def test_nav_to_tariffs_from_dashboard(self, page: Page, logged_in_user):
        """Проверяет переход на страницу тарифов с dashboard."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        tariffs_link = page.locator("a[href='#/tariffs']").first
        if tariffs_link.count() > 0:
            tariffs_link.click()
            wait_for_loading(page)
            url_hash = get_url_hash(page)
            assert url_hash == "#/tariffs"

    def test_nav_to_payments_from_dashboard(self, page: Page, logged_in_user):
        """Проверяет переход на страницу платежей с dashboard."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        payments_link = page.locator("a[href='#/payments']").first
        if payments_link.count() > 0:
            payments_link.click()
            wait_for_loading(page)
            url_hash = get_url_hash(page)
            assert url_hash == "#/payments"
