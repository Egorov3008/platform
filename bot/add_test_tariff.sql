-- Добавление тестового тарифа: 1 рубль, 30 дней
INSERT INTO tariff (id, name_tariff, amount, description, limit_ip, period, traffic_limit)
VALUES (11, 'тест', 1.0, 'Тестовый тариф на 30 дней', 0, 30, 0.0);
