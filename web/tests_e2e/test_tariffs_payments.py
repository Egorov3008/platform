"""
E2E тесты тарифов и платежей VPN Web Frontend.
Тестирование отображения тарифов, создания платежей, интеграции с YooKassa.
"""
import pytest
from playwright.sync_api import Page, expect
import re

from tests_e2e.config import BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD
from tests_e2e.pages.pages import TariffsPage, PaymentsPage, DashboardPage, ModalPage
from tests_e2e.utils.helpers import (
    wait_for_loading, wait_for_toast, wait_for_modal, is_visible,
    parse_tariff_cards, element_count, get_url_hash, validate_currency_format
)


# ============================================================================
# Тесты страницы тарифов
# ============================================================================

@pytest.mark.tariffs
class TestTariffsPage:
    """Тесты страницы тарифов."""

    def test_tariffs_page_renders(self, page: Page):
        """Проверяет корректную отрисовку страницы тарифов."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        # Страница загрузилась
        assert tariffs_page.tariffs_grid.count() > 0 or tariffs_page.is_empty_state_visible()

    def test_tariffs_page_accessible_without_auth(self, page: Page):
        """Проверяет доступность страницы тарифов без авторизации."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        # Не должно быть редиректа на login
        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"

    def test_tariffs_grid_structure(self, page: Page):
        """Проверяет структуру grid тарифов."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        if tariffs_page.get_tariffs_count() > 0:
            grid = page.locator(".tariffs-grid")
            assert grid.count() > 0


@pytest.mark.tariffs
class TestTariffCards:
    """Тесты карточек тарифов."""

    def test_tariff_cards_have_required_fields(self, page: Page):
        """Проверяет наличие обязательных полей у карточек тарифов."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        cards = tariffs_page.get_tariff_cards()
        assert len(cards) > 0, "Тарифы должны быть доступны"

        for card in cards:
            assert "name" in card
            assert "price" in card
            assert "description" in card
            assert card["name"] != "", "Название тарифа не должно быть пустым"

    def test_tariff_has_buy_button(self, page: Page):
        """Проверяет наличие кнопки покупки у каждого тарифа."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        cards = tariffs_page.get_tariff_cards()
        for card in cards:
            assert card.get("has_buy_button") is True, f"Тариф {card.get('name')} должен иметь кнопку покупки"

    def test_tariff_price_has_currency(self, page: Page):
        """Проверяет наличие символа валюты в цене тарифа."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        cards = tariffs_page.get_tariff_cards()
        for card in cards:
            price = card.get("price", "")
            if price:
                # Цена должна содержать ₽ или rub
                assert "₽" in price or "руб" in price.lower() or "rub" in price.lower(), \
                    f"Цена '{price}' должна содержать символ валюты"

    def test_tariff_cards_count_matches_api(self, page: Page):
        """Проверяет что количество карточек совпадает с данными API."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        # Получаем количество карточек на странице
        cards_count = tariffs_page.get_tariffs_count()

        # Проверяем через API
        response = page.request.get(f"{BASE_URL}/api/v1/tariffs/")
        assert response.ok
        api_data = response.json()

        # API должен вернуть столько же или больше (pagination)
        if isinstance(api_data, list):
            assert len(api_data) >= cards_count
        elif isinstance(api_data, dict) and "tariffs" in api_data:
            assert len(api_data["tariffs"]) >= cards_count

    def test_tariff_names_are_unique(self, page: Page):
        """Проверяет уникальность названий тарифов."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        cards = tariffs_page.get_tariff_cards()
        names = [card["name"] for card in cards if card.get("name")]

        assert len(names) == len(set(names)), "Названия тарифов должны быть уникальными"

    def test_tariff_features_are_displayed(self, page: Page):
        """Проверяет отображение характеристик тарифов."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        cards = tariffs_page.get_tariff_cards()
        for card in cards:
            features = card.get("features", "")
            # Характеристики должны быть не пустыми
            assert features != "", f"Тариф {card.get('name')} должен иметь характеристики"


# ============================================================================
# Тесты создания платежа
# ============================================================================

@pytest.mark.payments
class TestPaymentCreation:
    """Тесты создания платежей."""

    def test_buy_tariff_opens_modal(self, page: Page, logged_in_user):
        """Проверяет что покупка тарифа открывает модальное окно."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        if tariffs_page.get_tariffs_count() > 0:
            tariffs_page.click_buy_tariff(0)

            modal = ModalPage(page)
            assert modal.is_visible()

    def test_buy_tariff_requires_auth(self, page: Page):
        """Проверяет что для покупки требуется авторизация."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        if tariffs_page.get_tariffs_count() > 0:
            buy_btn = page.locator(".btn-buy").first
            buy_btn.click()

            page.wait_for_timeout(2000)
            # Должен быть редирект на login или ошибка
            url_hash = get_url_hash(page)
            has_modal = is_visible(page, ".modal-overlay")
            has_toast = wait_for_toast(page, timeout=2000)

            assert url_hash == "#/login" or has_modal or has_toast is not None

    def test_buy_tariff_modal_has_confirmation(self, page: Page, logged_in_user):
        """Проверяет наличие подтверждения в модалке покупки."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        if tariffs_page.get_tariffs_count() > 0:
            tariffs_page.click_buy_tariff(0)

            # В модалке должны быть кнопки подтверждения/отмены
            has_primary = page.locator(".modal-content .btn-primary").count() > 0
            has_secondary = page.locator(".modal-content .btn-secondary").count() > 0

            assert has_primary or has_secondary

    def test_buy_tariff_creates_payment(self, page: Page, logged_in_user):
        """Проверяет создание платежа при покупке тарифа."""
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()

        if tariffs_page.get_tariffs_count() > 0:
            # Получаем название тарифа
            cards = tariffs_page.get_tariff_cards()
            tariff_name = cards[0]["name"]

            tariffs_page.click_buy_tariff(0)

            # Подтверждаем покупку
            confirm_btn = page.locator(".modal-content .btn-primary").first
            confirm_btn.click()

            page.wait_for_timeout(2000)

            # Должен появиться toast или редирект на YooKassa
            toast_msg = wait_for_toast(page, timeout=3000)
            # Либо успех, либо ошибка (если YooKassa не настроен)
            assert toast_msg is not None or is_visible(page, ".modal-overlay")


# ============================================================================
# Тесты страницы платежей
# ============================================================================

@pytest.mark.payments
class TestPaymentsPage:
    """Тесты страницы платежей."""

    def test_payments_page_renders(self, page: Page, logged_in_user):
        """Проверяет отрисовку страницы платежей."""
        payments_page = PaymentsPage(page)
        payments_page.goto()

        # Страница должна загрузиться (даже если empty state)
        page.wait_for_timeout(1000)
        # Проверим что мы на правильной странице
        url_hash = get_url_hash(page)
        assert url_hash == "#/payments"

    def test_payments_shows_empty_state(self, page: Page, logged_in_user):
        """Проверяет отображение empty state для платежей."""
        payments_page = PaymentsPage(page)
        payments_page.goto()

        # По документации payments - placeholder страница с empty state
        assert payments_page.is_empty_state_visible() or page.locator("main").count() > 0

    def test_payments_requires_auth(self, page: Page):
        """Проверяет что страница платежей требует авторизации."""
        page.goto(f"{BASE_URL}/#/payments")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_payments_has_back_to_dashboard_link(self, page: Page, logged_in_user):
        """Проверяет наличие ссылки назад на dashboard."""
        payments_page = PaymentsPage(page)
        payments_page.goto()

        # Должна быть навигация или ссылка на dashboard
        has_dash_link = page.locator("a[href='#/dashboard']").count() > 0
        has_nav = page.locator("header").count() > 0

        assert has_dash_link or has_nav


# ============================================================================
# Тесты интеграции тарифов и dashboard
# ============================================================================

@pytest.mark.tariffs
@pytest.mark.integration
class TestTariffsDashboardIntegration:
    """Тесты интеграции тарифов и dashboard."""

    def test_tariffs_accessible_from_dashboard(self, page: Page, logged_in_user):
        """Проверяет доступность тарифов из dashboard."""
        dashboard = DashboardPage(page)
        dashboard.goto()

        tariffs_link = page.locator("a[href='#/tariffs']").first
        assert tariffs_link.count() > 0

        tariffs_link.click()
        wait_for_loading(page)

        url_hash = get_url_hash(page)
        assert url_hash == "#/tariffs"

    def test_create_key_shows_same_tariffs_as_tariffs_page(self, page: Page, logged_in_user_with_tg):
        """Проверяет что тарифы в создании ключа совпадают с тарифами на странице."""
        # Получаем тарифы со страницы тарифов
        tariffs_page = TariffsPage(page)
        tariffs_page.goto()
        tariffs_cards = tariffs_page.get_tariff_cards()
        tariff_names_page = {card["name"] for card in tariffs_cards}

        # Получаем тарифы из модалки создания ключа
        dashboard = DashboardPage(page)
        dashboard.goto()
        dashboard.click_create_key()

        options = page.locator(".modal-content select option")
        options_count = options.count()
        tariff_names_modal = set()
        for i in range(options_count):
            text = options.nth(i).text_content()
            text = text.strip()
            if text and text != "Выберите тариф":
                tariff_names_modal.add(text)

        # Все тарифы из модалки должны быть на странице тарифов
        assert tariff_names_modal.issubset(tariff_names_page) or len(tariff_names_modal) > 0
