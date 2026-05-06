# Тестирование платёжного flow

## Подготовка (одноразово)

```bash
# 1. Убедиться, что .env настроен:
cat .env | grep -E "LOG_LEVEL|DISABLE_WEBHOOK_IP_CHECK|DATABASE_URL"
# Ожидаемо:
# LOG_LEVEL=DEBUG
# DISABLE_WEBHOOK_IP_CHECK=true
# DATABASE_URL=postgresql://...

# 2. Запустить контейнеры
docker-compose up -d

# 3. Дождаться, пока backend стартует
docker-compose logs -f backend | grep "Application startup complete"
```

## Сценарий 1: Создание платежа (Bug 1)

```bash
# Откройте web в браузере: http://localhost:8001
# 1. Залогиньтесь (код от Telegram-бота)
# 2. Перейдите на #/tariffs
# 3. Нажмите "Купить" на любом тарифе
# 4. Появится модаль с выбором месяцев, нажмите "Перейти к оплате"

# В логах должны появиться DEBUG-сообщения:
docker-compose logs backend | grep -i "payment\|создан\|сохранен" | tail -20

# Проверьте БД:
docker-compose exec -T postgres psql -U egorov vpn_bot -c \
  "SELECT payment_id, tg_id, amount, status FROM payments ORDER BY created_at DESC LIMIT 1;"
```

## Сценарий 2: Проверка статуса платежа через web (Bug 2)

```bash
# После создания платежа:
# 1. Перейдите на #/payments
# 2. Должна быть запись с статусом "pending" и кнопка "Проверить"
# 3. Нажмите "Проверить" (до того как webhook подтвердит платёж)

# В логах будут DEBUG-сообщения о попытке получить статус:
docker-compose logs web | grep -i "get_payment_status\|проверка" | tail -5
```

## Сценарий 3: Имитация webhook и генерация ключа (Bug 3 + Bug 4)

```bash
# 1. Получите payment_id из БД:
PAYMENT_ID=$(docker-compose exec -T postgres psql -U egorov vpn_bot -t -c \
  "SELECT payment_id FROM payments ORDER BY created_at DESC LIMIT 1;" | tr -d ' \n')

echo "Использую payment_id: $PAYMENT_ID"

# 2. Запустите имитатор webhook:
cd /home/claude/vpn-platform
python backend/tools/test_webhook.py --event succeeded --payment-id "$PAYMENT_ID"

# Ожидаемый вывод: HTTP 200

# 3. Проверьте в логах, что webhook был обработан:
docker-compose logs backend | grep -i "webhook\|route\|succeeded" | tail -30

# 4. Проверьте, что статус платежа обновился:
docker-compose exec -T postgres psql -U egorov vpn_bot -c \
  "SELECT payment_id, status FROM payments WHERE payment_id = '$PAYMENT_ID';"
# Ожидаемо: status = succeeded

# 5. Проверьте, что ключ был создан:
docker-compose exec -T postgres psql -U egorov vpn_bot -c \
  "SELECT email, tg_id, created_at FROM keys ORDER BY created_at DESC LIMIT 1;"
# Ожидаемо: новая запись с тем же tg_id
```

## Сценарий 4: Проверка статуса через web после webhook

```bash
# 1. Вернитесь на #/payments
# 2. Нажмите F5 (refresh страницы) или автоматически обновится
# 3. Статус платежа должен измениться на "succeeded"
# 4. На #/dashboard должен появиться новый ключ
```

## Просмотр DEBUG-логов

### Backend (все компоненты)

```bash
# Все DEBUG-логи в консоли:
docker-compose logs backend 2>&1 | grep -i debug | head -50

# Или в файле logs/application.log:
docker-compose exec -T backend tail -f logs/application.log | grep -i debug

# Фильтр по trace_id (все логи одного запроса):
TRACE_ID=$(docker-compose logs backend | grep "trace_id" | head -1 | grep -o "[a-f0-9]\{8\}" | head -1)
docker-compose logs backend | grep "$TRACE_ID"
```

### Web API

```bash
# DEBUG-логи web:
docker-compose logs web 2>&1 | grep -i "debug\|post /payments\|get /payments" | head -50
```

### Все логи одного запроса

```bash
# Получите trace_id из заголовка ответа или из логов
# Затем фильтруйте по этому trace_id в обоих сервисах:
docker-compose logs | grep "<trace_id>"
```

## Проверка ошибок

```bash
# Ошибки backend:
docker-compose logs backend 2>&1 | grep -i "error\|exception" | tail -20

# Ошибки web:
docker-compose logs web 2>&1 | grep -i "error\|exception" | tail -20

# Все 500-ошибки:
docker-compose logs | grep -i "500\|traceback" | head -20
```

## Cleaning up

```bash
# Остановить контейнеры:
docker-compose down

# Удалить логи:
rm -rf backend/logs backend/logs_error web/logs
```

## Возможные проблемы и их решение

| Проблема | Решение |
|----------|---------|
| `HTTP 403 Webhook IP not allowed` | `DISABLE_WEBHOOK_IP_CHECK=true` в .env |
| `Payment not found` в webhook | Проверьте, что payment_id существует в БД перед вызовом webhook |
| Ключ не создаётся после webhook | Проверьте DEBUG-логи в `router.py:45` (извлечение операции) и `creation_service.py` |
| Платёж не сохраняется в БД | Проверьте DEBUG-логи в `base.py:save_data()` на предмет исключения |
| Логи не показывают DEBUG-сообщения | Убедитесь `LOG_LEVEL=DEBUG` в .env и перезапустите контейнеры |

