"""
Page Objects для E2E тестов VPN Web Frontend. (Sync API)
"""
from playwright.sync_api import Page, Locator, expect
from typing import Dict, List, Optional
from tests_e2e.config import BASE_URL, SELECTORS
from tests_e2e.utils.helpers import (
    wait_for_loading, wait_for_toast, wait_for_modal, close_modal,
    parse_key_cards, parse_tariff_cards, parse_admin_metrics,
    element_count, is_visible
)

class BasePage:
    """Базовый класс для всех страниц."""
    
    def __init__(self, page: Page):
        self.page = page
    
    def navigate(self, hash_path: str):
        """Переход к странице по хешу."""
        self.page.goto(f"{BASE_URL.rstrip('/')}{hash_path}")
        wait_for_loading(self.page)
    
    def get_toast_message(self) -> Optional[str]:
        """Получает сообщение тоста."""
        return wait_for_toast(self.page)
    
    def click_logout(self):
        """Кликает кнопку выхода."""
        self.page.locator(".btn-logout").first.click()
        wait_for_loading(self.page)


class LoginPage(BasePage):
    """Страница входа."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = page.locator("#loginEmail").first
        self.password_input = page.locator("#loginPassword").first
        self.submit_btn = page.locator("button[type='submit']").first
        self.telegram_login_btn = page.locator("text=Войти через Telegram").first
        self.register_link = page.locator("a[href='#/register']").first
    
    def goto(self):
        """Переход на страницу логина."""
        self.page.goto(f"{BASE_URL.rstrip('/')}/#/login")
        wait_for_loading(self.page)
    
    def login(self, email: str, password: str):
        """Выполняет вход."""
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_btn.click()
        self.page.wait_for_timeout(2000)
    
    def is_page_loaded(self) -> bool:
        """Проверяет загрузку страницы."""
        return is_visible(self.page, "#loginEmail")
    
    def has_telegram_login_option(self) -> bool:
        """Проверяет наличие кнопки входа через Telegram."""
        return self.telegram_login_btn.count() > 0
    
    def navigate_to_register(self):
        """Переход на страницу регистрации."""
        self.register_link.click()
        wait_for_loading(self.page)


class RegisterPage(BasePage):
    """Страница регистрации."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = page.locator("#regEmail").first
        self.password_input = page.locator("#regPassword").first
        self.tg_id_input = page.locator("#regTgId").first
        self.submit_btn = page.locator("button[type='submit']").first
        self.login_link = page.locator("a[href='#/login']").first
    
    def goto(self):
        """Переход на страницу регистрации."""
        self.page.goto(f"{BASE_URL.rstrip('/')}/#/register")
        wait_for_loading(self.page)
    
    def register(self, email: str, password: str, tg_id: Optional[str] = None):
        """Выполняет регистрацию."""
        self.email_input.fill(email)
        self.password_input.fill(password)
        if tg_id:
            self.tg_id_input.fill(tg_id)
        self.submit_btn.click()
        wait_for_loading(self.page)
    
    def is_page_loaded(self) -> bool:
        """Проверяет загрузку страницы."""
        return is_visible(self.page, "#registerEmail")
    
    def navigate_to_login(self):
        """Переход на страницу логина."""
        self.login_link.click()
        wait_for_loading(self.page)


class DashboardPage(BasePage):
    """Страница dashboard с VPN ключами."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.create_key_btn = page.locator(".btn-create-key").first
        self.keys_grid = page.locator(".keys-grid").first
        self.empty_state = page.locator(".empty-state").first
    
    def goto(self):
        """Переход на dashboard."""
        self.navigate("#/dashboard")
    
    def get_keys_count(self) -> int:
        """Получает количество ключей на странице."""
        return element_count(self.page, ".key-card")
    
    def get_key_cards(self) -> List[Dict]:
        """Получает данные всех карточек ключей."""
        return parse_key_cards(self.page)
    
    def is_empty_state_visible(self) -> bool:
        """Проверяет видимость пустого состояния."""
        return is_visible(self.page, ".empty-state")
    
    def is_create_key_visible(self) -> bool:
        """Проверяет видимость кнопки создания ключа."""
        return is_visible(self.page, ".btn-create-key")
    
    def click_create_key(self):
        """Кликает кнопку создания ключа."""
        self.create_key_btn.click()
        wait_for_modal(self.page)
    
    def renew_key(self, key_index: int = 0):
        """Продлевает ключ по индексу."""
        self.page.locator(".btn-renew").nth(key_index).click()
        wait_for_loading(self.page)
    
    def delete_key(self, key_index: int = 0):
        """Удаляет ключ по индексу."""
        self.page.locator(".btn-delete").nth(key_index).click()
        wait_for_loading(self.page)
    
    def copy_key(self, key_index: int = 0):
        """Копирует ключ по индексу."""
        self.page.locator(".btn-copy").nth(key_index).click()
        wait_for_loading(self.page)
    
    def has_key_with_name(self, name: str) -> bool:
        """Проверяет наличие ключа с именем."""
        cards = self.get_key_cards()
        return any(card.get("name") == name for card in cards)


class TariffsPage(BasePage):
    """Страница тарифов."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.tariffs_grid = page.locator(".tariffs-grid").first
    
    def goto(self):
        """Переход на страницу тарифов."""
        self.navigate("#/tariffs")
    
    def get_tariff_cards(self) -> List[Dict]:
        """Получает данные всех карточек тарифов."""
        return parse_tariff_cards(self.page)
    
    def get_tariffs_count(self) -> int:
        """Получает количество тарифов."""
        return element_count(self.page, ".tariff-card")
    
    def is_empty_state_visible(self) -> bool:
        """Проверяет видимость пустого состояния."""
        return is_visible(self.page, ".empty-state")
    
    def click_buy_tariff(self, tariff_index: int = 0):
        """Кликает кнопку покупки тарифа."""
        self.page.locator(".btn-buy").nth(tariff_index).click()
        wait_for_modal(self.page)


class PaymentsPage(BasePage):
    """Страница платежей."""
    
    def __init__(self, page: Page):
        super().__init__(page)
    
    def goto(self):
        """Переход на страницу платежей."""
        self.navigate("#/payments")
    
    def is_empty_state_visible(self) -> bool:
        """Проверяет видимость пустого состояния."""
        return is_visible(self.page, ".empty-state")


class AdminPage(BasePage):
    """Страница администратора."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.users_tab = page.locator("[data-tab='users']").first
        self.keys_tab = page.locator("[data-tab='keys']").first
    
    def goto(self):
        """Переход на страницу администратора."""
        self.navigate("#/admin")
    
    def get_metrics(self) -> Dict[str, str]:
        """Получает метрики dashboard."""
        return parse_admin_metrics(self.page)
    
    def get_metrics_count(self) -> int:
        """Получает количество метрических карточек."""
        return element_count(self.page, ".metric-card")
    
    def switch_to_users_tab(self):
        """Переключает на вкладку пользователей."""
        self.users_tab.click()
        wait_for_loading(self.page)
    
    def switch_to_keys_tab(self):
        """Переключает на вкладку ключей."""
        self.keys_tab.click()
        wait_for_loading(self.page)
    
    def get_users_count(self) -> int:
        """Получает количество пользователей в таблице."""
        return self.page.locator(".users-table tbody tr").count()
    
    def get_keys_count_in_table(self) -> int:
        """Получает количество ключей в таблице."""
        return self.page.locator(".keys-table tbody tr").count()
    
    def block_user(self, user_index: int = 0):
        """Блокирует пользователя."""
        self.page.locator(".btn-block").nth(user_index).click()
        wait_for_loading(self.page)
    
    def unblock_user(self, user_index: int = 0):
        """Разблокирует пользователя."""
        self.page.locator(".btn-unblock").nth(user_index).click()
        wait_for_loading(self.page)
    
    def make_admin(self, user_index: int = 0):
        """Делает пользователя администратором."""
        self.page.locator(".btn-make-admin").nth(user_index).click()
        wait_for_loading(self.page)
    
    def delete_key(self, key_index: int = 0):
        """Удаляет ключ из админ-панели."""
        self.page.locator(".keys-table .btn-danger").nth(key_index).click()
        wait_for_loading(self.page)


class ModalPage(BasePage):
    """Хелпер для работы с модальными окнами."""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.overlay = page.locator(".modal-overlay").first
        self.content = page.locator(".modal-content").first
        self.close_btn = page.locator(".modal-close").first
        self.title = page.locator(".modal-title").first
    
    def is_visible(self) -> bool:
        """Проверяет видимость модального окна."""
        return is_visible(self.page, ".modal-overlay")
    
    def get_title(self) -> str:
        """Получает заголовок модального окна."""
        text = self.title.text_content()
        return text.strip() if text else ""
    
    def close(self):
        """Закрывает модальное окно."""
        close_modal(self.page)
    
    def select_tariff_and_create(self, tariff_name: str):
        """Выбирает тариф в модалке создания ключа."""
        select = self.page.locator("select").first
        if select.count() > 0:
            select.select_option(label=tariff_name)
        self.page.locator(".btn-primary").first.click()
        wait_for_loading(self.page)


class MobileNavigation:
    """Хелпер для мобильной навигации."""
    
    def __init__(self, page: Page):
        self.page = page
        self.toggle_btn = page.locator(".nav-toggle").first
        self.mobile_menu = page.locator(".nav-mobile").first
    
    def open_menu(self):
        """Открывает мобильное меню."""
        self.toggle_btn.click()
        self.page.wait_for_timeout(300)
    
    def is_menu_open(self) -> bool:
        """Проверяет открытость меню."""
        return is_visible(self.page, ".nav-mobile")
    
    def click_link(self, link_selector: str):
        """Кликает по ссылке в мобильном меню."""
        if not self.is_menu_open():
            self.open_menu()
        self.page.locator(link_selector).first.click()
        wait_for_loading(self.page)
