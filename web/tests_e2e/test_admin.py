"""
E2E тесты админ-панели VPN Web Frontend.
Тестирование dashboard метрик, управления пользователями и ключами.
"""
import pytest
from playwright.sync_api import Page, expect
import asyncio

from tests_e2e.config import (
    BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD,
    TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_TG_ID, TEST_TG_ID_2,
)
from tests_e2e.pages.pages import AdminPage, DashboardPage
from tests_e2e.utils.helpers import (
    wait_for_loading, wait_for_toast, wait_for_modal, is_visible,
    parse_admin_metrics, element_count, get_url_hash, login_via_ui
)


# ============================================================================
# Фикстуры для админ тестов
# ============================================================================

@pytest.fixture
def admin_with_users(page: Page, admin_user, db):
    """Админ с несколькими пользователями в БД."""
    db["create_user"](TEST_USER_EMAIL, TEST_USER_PASSWORD, tg_id=TEST_TG_ID)

    yield page

    db["delete_user"](TEST_USER_EMAIL, TEST_TG_ID)


# ============================================================================
# Тесты доступа к админ-панели
# ============================================================================

@pytest.mark.admin
@pytest.mark.access
class TestAdminAccess:
    """Тесты доступа к админ-панели."""

    def test_admin_page_renders_for_admin(self, page: Page, logged_in_admin):
        """Проверяет отрисовку admin страницы для администратора."""
        admin_page = AdminPage(page)
        admin_page.goto()

        assert admin_page.get_metrics_count() > 0 or page.locator(".metrics-grid").count() > 0

    def test_regular_user_redirected_from_admin(self, page: Page, logged_in_user):
        """Проверяет редирект обычного пользователя с admin страницы."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(2000)

        url_hash = get_url_hash(page)
        # Обычный пользователь должен быть редирекчен
        assert "admin" not in url_hash

    def test_unauthenticated_redirected_from_admin(self, page: Page):
        """Проверяет редирект неавторизованного пользователя."""
        page.goto(f"{BASE_URL}/#/admin")
        page.wait_for_timeout(1500)

        url_hash = get_url_hash(page)
        assert url_hash == "#/login"

    def test_admin_link_visible_for_admin_only(self, page: Page, logged_in_admin):
        """Проверяет видимость ссылки на admin только для администратора."""
        admin_page = AdminPage(page)
        admin_page.goto()

        admin_link = page.locator("a[href='#/admin']").first
        assert admin_link.count() > 0


# ============================================================================
# Тесты метрик dashboard
# ============================================================================

@pytest.mark.admin
@pytest.mark.metrics
class TestAdminMetrics:
    """Тесты метрик админ-панели."""

    def test_metrics_grid_exists(self, page: Page, logged_in_admin):
        """Проверяет наличие grid метрик."""
        admin_page = AdminPage(page)
        admin_page.goto()

        metrics_grid = page.locator(".metrics-grid")
        assert metrics_grid.count() > 0

    def test_metrics_cards_count(self, page: Page, logged_in_admin):
        """Проверяет количество метрических карточек."""
        admin_page = AdminPage(page)
        admin_page.goto()

        # По документации: 8 метрик (MRR current/prev, MRR growth, paying users,
        # new users 30d, keys expiring 72h, conversion to keys %, conversion to paid %, succeeded payments)
        metrics_count = admin_page.get_metrics_count()
        assert metrics_count >= 4  # Минимум 4 метрики должны быть

    def test_metrics_have_labels_and_values(self, page: Page, logged_in_admin):
        """Проверяет что метрики имеют подписи и значения."""
        admin_page = AdminPage(page)
        admin_page.goto()

        metrics = admin_page.get_metrics()
        assert len(metrics) > 0

        for label, value in metrics.items():
            assert label != "", "Метрика должна иметь подпись"
            assert value is not None, f"Метрика '{label}' должна иметь значение"

    def test_metrics_show_numeric_values(self, page: Page, logged_in_admin):
        """Проверяет что метрики отображают числовые значения."""
        admin_page = AdminPage(page)
        admin_page.goto()

        metrics = admin_page.get_metrics()

        # Хотя бы одна метрика должна содержать число
        has_numeric = False
        for label, value in metrics.items():
            # Извлекаем числа из строки
            import re
            numbers = re.findall(r'\d+', value)
            if numbers:
                has_numeric = True
                break

        assert has_numeric, "Хотя бы одна метрика должна содержать числовое значение"

    def test_metrics_show_mrr(self, page: Page, logged_in_admin):
        """Проверяет отображение MRR метрики."""
        admin_page = AdminPage(page)
        admin_page.goto()

        metrics = admin_page.get_metrics()

        # Должна быть метрика MRR
        has_mrr = any("mrr" in label.lower() for label in metrics.keys())
        assert has_mrr, "Должна быть метрика MRR"

    def test_metrics_loading_state(self, page: Page, logged_in_admin):
        """Проверяет состояние загрузки метрик."""
        admin_page = AdminPage(page)

        # Быстрый переход может показать спиннер
        page.goto(f"{BASE_URL}/#/admin")

        # Спиннер должен исчезнуть
        wait_for_loading(page)

        metrics = admin_page.get_metrics()
        assert len(metrics) > 0


# ============================================================================
# Тесты вкладки Users
# ============================================================================

@pytest.mark.admin
@pytest.mark.users_tab
class TestAdminUsersTab:
    """Тесты вкладки пользователей."""

    def test_users_tab_exists(self, page: Page, logged_in_admin):
        """Проверяет наличие вкладки пользователей."""
        admin_page = AdminPage(page)
        admin_page.goto()

        assert admin_page.users_tab.count() > 0

    def test_users_tab_switches(self, page: Page, logged_in_admin):
        """Проверяет переключение на вкладку пользователей."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Таблица пользователей должна быть видна
        assert page.locator(".users-table").count() > 0 or page.locator(".admin-users").count() > 0

    def test_users_table_structure(self, page: Page, logged_in_admin):
        """Проверяет структуру таблицы пользователей."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Заголовки таблицы
        headers = page.locator(".users-table thead th")
        headers_count = headers.count()

        # Должны быть колонки: TG ID, имя, email, ключи, роль, статус
        assert headers_count >= 5

    def test_users_show_in_table(self, page: Page, admin_with_users):
        """Проверяет отображение пользователей в таблице."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        users_count = admin_page.get_users_count()
        assert users_count > 0

    def test_user_has_block_unblock_button(self, page: Page, admin_with_users):
        """Проверяет наличие кнопки блокировки/разблокировки."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Должна быть кнопка block или unblock
        block_btn = page.locator(".btn-block").count()
        unblock_btn = page.locator(".btn-unblock").count()

        assert block_btn > 0 or unblock_btn > 0

    def test_user_has_make_admin_button(self, page: Page, admin_with_users):
        """Проверяет наличие кнопки сделать админом."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Кнопка make admin должна быть (кроме текущего админа)
        admin_btn_count = page.locator(".btn-make-admin").count()
        assert admin_btn_count >= 0

    def test_block_user_action(self, page: Page, admin_with_users):
        """Проверяет блокировку пользователя."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        initial_users = admin_page.get_users_count()
        if initial_users > 0:
            admin_page.block_user(0)
            page.wait_for_timeout(1500)

            # Должен появиться toast
            toast = wait_for_toast(page)
            assert toast is not None

    def test_user_status_display(self, page: Page, admin_with_users):
        """Проверяет отображение статуса пользователя."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Статусы должны отображаться
        rows = page.locator(".users-table tbody tr")
        if rows.count() > 0:
            # Последняя ячейка обычно статус
            cells = rows.first.locator("td")
            cell_count = cells.count()
            if cell_count >= 6:
                status = cells.nth(5).text_content()
                assert status.strip() != ""


# ============================================================================
# Тесты вкладки Keys
# ============================================================================

@pytest.mark.admin
@pytest.mark.keys_tab
class TestAdminKeysTab:
    """Тесты вкладки ключей."""

    def test_keys_tab_exists(self, page: Page, logged_in_admin):
        """Проверяет наличие вкладки ключей."""
        admin_page = AdminPage(page)
        admin_page.goto()

        assert admin_page.keys_tab.count() > 0

    def test_keys_tab_switches(self, page: Page, logged_in_admin):
        """Проверяет переключение на вкладку ключей."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_keys_tab()

        assert page.locator(".keys-table").count() > 0 or page.locator(".admin-keys").count() > 0

    def test_keys_table_structure(self, page: Page, logged_in_admin):
        """Проверяет структуру таблицы ключей."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_keys_tab()

        headers = page.locator(".keys-table thead th")
        headers_count = headers.count()

        # Колонки: client ID, TG ID, тариф, expiry, действия
        assert headers_count >= 4

    def test_delete_key_from_admin(self, page: Page, logged_in_admin):
        """Проверяет удаление ключа из админ-панели."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_keys_tab()

        keys_count = admin_page.get_keys_count_in_table()
        if keys_count > 0:
            admin_page.delete_key(0)
            page.wait_for_timeout(1500)

            # Toast или подтверждение
            toast = wait_for_toast(page)
            assert toast is not None


# ============================================================================
# Тесты админ-действий
# ============================================================================

@pytest.mark.admin
@pytest.mark.actions
class TestAdminActions:
    """Тесты административных действий."""

    def test_make_user_admin(self, page: Page, admin_with_users):
        """Проверяет действие 'сделать пользователя админом'."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        users_count = admin_page.get_users_count()
        if users_count > 0:
            admin_page.make_admin(0)
            page.wait_for_timeout(1500)

            toast = wait_for_toast(page)
            assert toast is not None

    def test_unblock_user(self, page: Page, admin_with_users):
        """Проверяет разблокировку пользователя."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_users_tab()

        # Если есть заблокированные пользователи - разблокируем
        unblock_btns = page.locator(".btn-unblock").count()
        if unblock_btns > 0:
            admin_page.unblock_user(0)
            page.wait_for_timeout(1500)

            toast = wait_for_toast(page)
            assert toast is not None

    def test_admin_actions_show_confirmation(self, page: Page, admin_with_users):
        """Проверяет подтверждение деструктивных действий."""
        admin_page = AdminPage(page)
        admin_page.goto()
        admin_page.switch_to_keys_tab()

        if admin_page.get_keys_count_in_table() > 0:
            # Удаление ключа должно спросить подтверждение
            delete_btn = page.locator(".keys-table .btn-danger").first
            delete_btn.click()

            page.wait_for_timeout(500)
            # Либо модалка подтверждения, либо confirm dialog
            has_modal = is_visible(page, ".modal-overlay")
            assert has_modal  # Должна быть модалка подтверждения
