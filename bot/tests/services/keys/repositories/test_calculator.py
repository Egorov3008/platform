from datetime import datetime, timedelta


from logger import logger
from tests.conftest import convert_ms_to_date


class TestExpiryCalculator:
    def test_key_duration_new_key_default_months(self, expiry_calculator):
        # Тест для одного месяца (по умолчанию)
        days = 30
        result_timestamp = expiry_calculator.key_duration_new_key(days)

        # Проверяем, что timestamp не None и является целым числом
        assert result_timestamp is not None
        # Проверяем, что время expiry соответствует примерно 30 дням в будущем
        result_datetime = datetime.fromtimestamp(result_timestamp / 1000)
        expected_datetime = datetime.now() + timedelta(days=30)

        # Разница не должна превышать 1 секунду
        assert abs((result_datetime - expected_datetime).total_seconds()) < 1

    def test_key_duration_new_key_multiple_months(self, expiry_calculator):
        # Тест для нескольких месяцев
        days_per_month = 30
        number_of_months = 3

        result_timestamp = expiry_calculator.key_duration_new_key(
            days=days_per_month, number_of_months=number_of_months
        )
        assert result_timestamp is not None
        result_datetime = datetime.fromtimestamp(result_timestamp / 1000)
        expected_datetime = datetime.now() + timedelta(
            days=days_per_month * number_of_months
        )

        assert abs((result_datetime - expected_datetime).total_seconds()) < 1

    def test_key_duration_existing_key_future_expiry(self, expiry_calculator, key):
        # Тест когда expiry_time ключа в будущем
        key.expiry_time = int((datetime.now() + timedelta(days=10)).timestamp() * 1000)
        expiry_time = convert_ms_to_date(key.expiry_time)
        result_timestamp = expiry_calculator.key_duration(key_details=key, days=20)
        # Ожидаем, что новое время будет 10 + 20 = 30 дней от текущего момента
        expected_datetime = datetime.now() + timedelta(days=30)
        result_expiry_datetime = convert_ms_to_date(result_timestamp)
        assert expected_datetime.strftime("%Y-%m-%d %H:%M") == result_expiry_datetime
        logger.debug(
            f"\nВремя истечения ключа {expiry_time}\n"
            f"Ожидаемое время: {expected_datetime.strftime('%Y-%m-%d %H:%M')}\n"
            f"Результат: {result_expiry_datetime}"
        )

    def test_key_duration_existing_key_past_expiry(self, expiry_calculator, key):
        # Тест когда expiry_time ключа в прошлом
        past_time = datetime.now() - timedelta(days=5)
        key.expiry_time = int(past_time.timestamp() * 1000)
        expiry_time = convert_ms_to_date(key.expiry_time)
        result_timestamp = expiry_calculator.key_duration(key_details=key, days=20)
        # Ожидаем, что новое время будет 20 дней от текущего момента (так как expiry в прошлом)
        expected_datetime = datetime.now() + timedelta(days=20)
        result_expiry_datetime = convert_ms_to_date(result_timestamp)
        assert expected_datetime.strftime("%Y-%m-%d %H:%M") == result_expiry_datetime
        logger.debug(
            f"\nВремя истечения ключа {expiry_time}\n"
            f"Ожидаемое время: {expected_datetime.strftime('%Y-%m-%d %H:%M')}\n"
            f"Результат: {result_expiry_datetime}"
        )

    def test_key_duration_with_multiple_months(self, expiry_calculator, key):
        # Тест с несколькими месяцами
        key.expiry_time = int((datetime.now() + timedelta(days=10)).timestamp() * 1000)

        result_timestamp = expiry_calculator.key_duration(
            key_details=key, days=30, number_of_months=2
        )

        # Ожидаем, что новое время будет 10 + 60 = 70 дней от текущего момента
        expected_datetime = datetime.now() + timedelta(days=70)
        result_expiry_datetime = datetime.fromtimestamp(result_timestamp / 1000)

        assert abs((result_expiry_datetime - expected_datetime).total_seconds()) < 1
