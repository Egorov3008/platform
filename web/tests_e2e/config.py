"""
Конфигурация тестовых данных для E2E тестов VPN Web Frontend.
"""
import os

# Базовый URL приложения
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Тестовые пользователи
TEST_USER_EMAIL = "test-e2e@example.com"
TEST_USER_PASSWORD = "TestPassword123!"

TEST_USER_2_EMAIL = "test-e2e-2@example.com"
TEST_USER_2_PASSWORD = "TestPassword456!"

# Администратор (создается через миграции)
ADMIN_EMAIL = "admin-e2e@example.com"
ADMIN_PASSWORD = "AdminPassword123!"

# Telegram тестовые данные
TEST_TG_ID = "999999999"
TEST_TG_ID_2 = "888888888"

# Тестовый тариф (создается через миграции)
DEFAULT_TARIFF_NAME = "Базовый"

# Таймауты
TIMEOUT_SHORT = 3000  # Короткие ожидания (анимации, тосты)
TIMEOUT_MEDIUM = 5000  # Средние ожидания (запросы API)
TIMEOUT_LONG = 10000  # Долгие ожидания (загрузка страниц)

# Размеры viewport для тестирования адаптивности
VIEWPORTS = {
    "mobile": {"width": 375, "height": 812},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1280, "height": 720},
}

# Селекторы (реальные селекторы фронтенда)
SELECTORS = {
    # Навигация
    "nav_header": "header .nav-links",
    "nav_mobile_toggle": ".nav-toggle",
    "nav_mobile_menu": ".nav-mobile",
    "nav_link_dashboard": "a[href='#/dashboard']",
    "nav_link_tariffs": "a[href='#/tariffs']",
    "nav_link_payments": "a[href='#/payments']",
    "nav_link_admin": "a[href='#/admin']",
    "nav_link_login": "a[href='#/login']",
    "nav_link_register": "a[href='#/register']",
    "nav_logout_btn": ".btn-logout",
    
    # Страница логина
    "login_email": "#loginEmail",
    "login_password": "#loginPassword",
    "login_submit": "button[type='submit']",
    "login_telegram_btn": "text=Войти через Telegram",
    "login_to_register": "a[href='#/register']",
    
    # Страница регистрации
    "register_email": "#regEmail",
    "register_password": "#regPassword",
    "register_tg_id": "#regTgId",
    "register_submit": "button[type='submit']",
    "register_to_login": "a[href='#/login']",
    
    # Dashboard
    "dashboard_page": ".page-dashboard",
    "keys_grid": ".keys-grid",
    "key_card": ".key-card",
    "key_card_empty": ".empty-state",
    "create_key_btn": ".btn-create-key",
    "key_copy_btn": ".btn-copy",
    "key_renew_btn": ".btn-renew",
    "key_delete_btn": ".btn-delete",
    
    # Тарифы
    "tariffs_page": ".page-tariffs",
    "tariffs_grid": ".tariffs-grid",
    "tariff_card": ".tariff-card",
    "tariff_buy_btn": ".btn-buy",
    
    # Админ панель
    "admin_page": ".page-admin",
    "admin_metrics": ".metrics-grid",
    "admin_metric_card": ".metric-card",
    "admin_tabs": ".admin-tabs",
    "admin_tab_users": "[data-tab='users']",
    "admin_tab_keys": "[data-tab='keys']",
    "admin_users_table": ".users-table",
    "admin_keys_table": ".keys-table",
    
    # Модальные окна
    "modal_overlay": ".modal-overlay",
    "modal_content": ".modal-content",
    "modal_close": ".modal-close",
    "modal_title": ".modal-title",
    
    # Тосты
    "toast_container": ".toast-container",
    "toast": ".toast",
    "toast_success": ".toast.success",
    "toast_error": ".toast.error",
    
    # Общие элементы
    "loading_spinner": ".loading-spinner",
    "page_title": ".page-title",
    "empty_state": ".empty-state",
    "btn_primary": ".btn-primary",
    "btn_secondary": ".btn-secondary",
    "btn_danger": ".btn-danger",
}
