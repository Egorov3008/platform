"""
Утилиты для E2E тестирования VPN Web Frontend.
Хелперы для парсинга DOM, ожидания, валидации. (Sync API)
"""
import re
from playwright.sync_api import Page, Locator, expect
from typing import Dict, List, Optional

from tests_e2e.config import SELECTORS, TIMEOUT_SHORT, TIMEOUT_MEDIUM, TIMEOUT_LONG, BASE_URL


# ============================================================================
# DOM парсинг
# ============================================================================

def parse_text_content(page: Page, selector: str) -> str:
    """Получает текстовое содержимое элемента."""
    element = page.locator(selector).first
    text = element.text_content()
    return text.strip() if text else ""


def parse_all_text_contents(page: Page, selector: str) -> List[str]:
    """Получает текстовое содержимое всех элементов."""
    elements = page.locator(selector)
    texts = []
    for el in elements.all():
        text = el.text_content()
        texts.append(text.strip() if text else "")
    return texts


def get_attribute(page: Page, selector: str, attribute: str) -> Optional[str]:
    """Получает значение атрибута элемента."""
    element = page.locator(selector).first
    return element.get_attribute(attribute)


def get_all_attributes(page: Page, selector: str, attribute: str) -> List[str]:
    """Получает значения атрибутов всех элементов."""
    elements = page.locator(selector)
    attrs = []
    for el in elements.all():
        attrs.append(el.get_attribute(attribute) or "")
    return attrs


def parse_key_cards(page: Page) -> List[Dict[str, str]]:
    """Парсит карточки ключей на dashboard."""
    cards = page.locator(".key-card")
    keys = []
    for card in cards.all():
        key_data = {
            "name": _text(card, ".key-name"),
            "tariff": _text(card, ".key-tariff"),
            "expiry": _text(card, ".key-expiry"),
            "status": _text(card, ".status-badge"),
            "traffic": _text(card, ".traffic-info"),
            "has_copy_button": card.locator(".btn-copy").count() > 0,
            "has_renew_button": card.locator(".btn-renew").count() > 0,
            "has_delete_button": card.locator(".btn-delete").count() > 0,
        }
        keys.append(key_data)
    return keys


def parse_tariff_cards(page: Page) -> List[Dict[str, str]]:
    """Парсит карточки тарифов."""
    cards = page.locator(".tariff-card")
    tariffs = []
    for card in cards.all():
        tariff_data = {
            "name": _text(card, ".tariff-name"),
            "price": _text(card, ".tariff-price"),
            "description": _text(card, ".tariff-description"),
            "features": _text(card, ".tariff-features"),
            "has_buy_button": card.locator(".btn-buy").count() > 0,
        }
        tariffs.append(tariff_data)
    return tariffs


def parse_admin_metrics(page: Page) -> Dict[str, str]:
    """Парсит метрики на странице администратора."""
    metric_cards = page.locator(".metric-card")
    metrics = {}
    for card in metric_cards.all():
        label = _text(card, ".metric-label")
        value = _text(card, ".metric-value")
        if label and value:
            metrics[label] = value
    return metrics


def parse_admin_users_table(page: Page) -> List[Dict[str, str]]:
    """Парсит таблицу пользователей в админ-панели."""
    rows = page.locator(".users-table tbody tr")
    users = []
    for row in rows.all():
        cells = row.locator("td")
        if cells.count() >= 6:
            users.append({
                "tg_id": cells.nth(0).text_content() or "",
                "name": cells.nth(1).text_content() or "",
                "email": cells.nth(2).text_content() or "",
                "keys_count": cells.nth(3).text_content() or "",
                "role": cells.nth(4).text_content() or "",
                "status": cells.nth(5).text_content() or "",
            })
    return users


def parse_admin_keys_table(page: Page) -> List[Dict[str, str]]:
    """Парсит таблицу ключей в админ-панели."""
    rows = page.locator(".keys-table tbody tr")
    keys = []
    for row in rows.all():
        cells = row.locator("td")
        if cells.count() >= 5:
            keys.append({
                "client_id": cells.nth(0).text_content() or "",
                "tg_id": cells.nth(1).text_content() or "",
                "tariff": cells.nth(2).text_content() or "",
                "expiry": cells.nth(3).text_content() or "",
                "has_delete_button": cells.nth(4).locator("button").count() > 0,
            })
    return keys


def _text(locator: Locator, selector: str) -> str:
    """Безопасно получает текст из вложенного элемента."""
    element = locator.locator(selector).first
    text = element.text_content()
    return text.strip() if text else ""


# ============================================================================
# Ожидания и проверки
# ============================================================================

def is_visible(page: Page, selector: str, timeout: int = TIMEOUT_MEDIUM) -> bool:
    """Проверяет видимость элемента."""
    try:
        expect(page.locator(selector).first).to_be_visible(timeout=timeout)
        return True
    except:
        return False


def is_hidden(page: Page, selector: str, timeout: int = TIMEOUT_SHORT) -> bool:
    """Проверяет скрытость элемента."""
    try:
        expect(page.locator(selector).first).to_be_hidden(timeout=timeout)
        return True
    except:
        return False


def element_count(page: Page, selector: str) -> int:
    """Возвращает количество элементов."""
    return page.locator(selector).count()


def wait_for_loading(page: Page, timeout: int = TIMEOUT_LONG):
    """Ожидает исчезновения спиннера загрузки."""
    try:
        page.locator(".loading-spinner").wait_for(state="hidden", timeout=timeout)
    except:
        pass


def wait_for_toast(page: Page, timeout: int = TIMEOUT_MEDIUM) -> Optional[str]:
    """Ожидает появления тоста и возвращает его текст."""
    try:
        toast = page.locator(".toast").first
        toast.wait_for(state="visible", timeout=timeout)
        text = toast.text_content()
        return text.strip() if text else None
    except:
        return None


def wait_for_modal(page: Page, timeout: int = TIMEOUT_MEDIUM):
    """Ожидает появления модального окна."""
    page.locator(".modal-overlay").wait_for(state="visible", timeout=timeout)


def close_modal(page: Page):
    """Закрывает модальное окно."""
    close_btn = page.locator(".modal-close").first
    if close_btn.count() > 0:
        close_btn.click()
    else:
        page.locator(".modal-overlay").click()


def get_url_hash(page: Page) -> str:
    """Получает текущий хеш URL (включая #)."""
    url = page.url
    if "#" in url:
        return "#" + url.split("#")[1]
    return ""


# ============================================================================
# Интерактивные хелперы
# ============================================================================

def login_via_ui(page: Page, email: str, password: str):
    """Выполняет вход через UI."""
    page.goto(f"{BASE_URL}/#/login")
    page.wait_for_timeout(1000)
    page.fill("#loginEmail", email)
    page.fill("#loginPassword", password)
    page.click("button[type='submit']")
    wait_for_loading(page)


def register_via_ui(page: Page, email: str, password: str, tg_id: Optional[str] = None):
    """Выполняет регистрацию через UI."""
    page.goto(f"{BASE_URL}/#/register")
    page.wait_for_timeout(1000)
    page.fill("#regEmail", email)
    page.fill("#regPassword", password)
    if tg_id:
        page.fill("#regTgId", tg_id)
    page.click("button[type='submit']")
    wait_for_loading(page)


# ============================================================================
# Валидация контента
# ============================================================================

def validate_email_format(email: str) -> bool:
    """Проверяет формат email."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_date_format(date_str: str) -> bool:
    """Проверяет формат даты (ДД.ММ.ГГГГ)."""
    return bool(re.match(r'\d{2}\.\d{2}\.\d{4}', date_str))


def validate_currency_format(price_str: str) -> bool:
    """Проверяет формат цены."""
    return bool(re.match(r'\d+\s*₽', price_str))


def validate_uuid_format(uuid_str: str) -> bool:
    """Проверяет формат UUID."""
    return bool(re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', uuid_str, re.IGNORECASE))


# ============================================================================
# localStorage хелперы (через evaluate)
# ============================================================================

def get_local_storage(page: Page) -> Dict[str, str]:
    """Получает содержимое localStorage."""
    return page.evaluate("() => JSON.parse(JSON.stringify(localStorage))")


def get_access_token(page: Page) -> Optional[str]:
    """Получает access token из localStorage."""
    storage = get_local_storage(page)
    return storage.get("access_token")


def get_refresh_token(page: Page) -> Optional[str]:
    """Получает refresh token из localStorage."""
    storage = get_local_storage(page)
    return storage.get("refresh_token")


def clear_local_storage(page: Page):
    """Очищает localStorage."""
    page.evaluate("() => localStorage.clear()")


def set_local_storage_item(page: Page, key: str, value: str):
    """Устанавливает элемент в localStorage."""
    page.evaluate(f"() => localStorage.setItem('{key}', '{value}')")
