"""
E2E тесты отображения времени платежа в истории платежей.
Проверяет формат даты и времени DD.MM.YYYY HH:MM.
"""
import pytest
import re
from playwright.sync_api import Page, expect

from tests_e2e.config import BASE_URL, TEST_TG_ID
from tests_e2e.utils.helpers import login_via_ui


class TestPaymentHistoryTimestamp:
    """Тесты отображения временной метки платежа."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Подготовка: вход в систему перед каждым тестом."""
        login_via_ui(page)
        page.goto(f"{BASE_URL}#/payments")
        page.wait_for_selector("table tbody tr", timeout=5000)

    def test_payment_timestamp_format(self, page: Page):
        """Проверка: платеж отображается в формате DD.MM.YYYY HH:MM."""
        # Получить содержимое первой ячейки даты в таблице
        date_cell = page.locator("table tbody tr:first-child td:first-child").text_content()

        # Проверить формат: DD.MM.YYYY HH:MM
        # Пример: "06.05.2026 18:30"
        timestamp_regex = r'^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$'
        assert re.match(timestamp_regex, date_cell), (
            f"Timestamp '{date_cell}' не соответствует формату DD.MM.YYYY HH:MM"
        )

    def test_payment_table_structure_intact(self, page: Page):
        """Проверка: структура таблицы не нарушена после добавления времени."""
        # Проверить количество столбцов (Дата, Сумма, Тип, Статус, Кнопка)
        header_count = page.locator("table thead th").count()
        expect.soft(header_count).to_equal(5)

        # Проверить наличие как минимум одной строки
        row_count = page.locator("table tbody tr").count()
        expect.soft(row_count).to_be_greater_than_or_equal(1)

    def test_payment_columns_alignment(self, page: Page):
        """Проверка: столбцы таблицы остаются выравненными."""
        # Проверить видимость всех основных столбцов
        date_col = page.locator("table tbody tr:first-child td:nth-child(1)")
        amount_col = page.locator("table tbody tr:first-child td:nth-child(2)")
        type_col = page.locator("table tbody tr:first-child td:nth-child(3)")
        status_col = page.locator("table tbody tr:first-child td:nth-child(4)")

        # Все столбцы должны быть видимы
        expect.soft(date_col).to_be_visible()
        expect.soft(amount_col).to_be_visible()
        expect.soft(type_col).to_be_visible()
        expect.soft(status_col).to_be_visible()

    def test_no_timestamp_formatting_errors(self, page: Page):
        """Проверка: нет ошибок в консоли при отображении временных меток."""
        # Собрать все сообщения об ошибках из консоли
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        # Перезагрузить страницу платежей
        page.reload()
        page.wait_for_selector("table tbody tr", timeout=5000)

        # Проверить отсутствие ошибок
        assert len(errors) == 0, f"Обнаружены ошибки консоли: {[e.text for e in errors]}"

    def test_multiple_payment_timestamps_formatted(self, page: Page):
        """Проверка: все платежи отображаются с корректным форматом времени."""
        # Получить все ячейки дат
        date_cells = page.locator("table tbody tr td:first-child").all_text_contents()

        timestamp_regex = r'^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$'

        # Проверить каждый платеж (кроме em-dash для null)
        for i, date_text in enumerate(date_cells):
            # Em-dash (—) - допустимое значение для null created_at
            if date_text.strip() == '—':
                continue
            assert re.match(timestamp_regex, date_text), (
                f"Платеж {i}: '{date_text}' не соответствует формату DD.MM.YYYY HH:MM"
            )
