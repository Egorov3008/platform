# 📊 Руководство по работе с мониторингом

## 🚀 Запуск стека мониторинга

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.monitoring.yml up -d

# Проверка статуса
docker-compose -f docker-compose.monitoring.yml ps

# Просмотр логов
docker-compose -f docker-compose.monitoring.yml logs -f loki
docker-compose -f docker-compose.monitoring.yml logs -f prometheus
docker-compose -f docker-compose.monitoring.yml logs -f tempo

# Остановка
docker-compose -f docker-compose.monitoring.yml down
```

---

## 🔍 Prometheus (http://localhost:9092)

### Назначение
Сбор и хранение метрик, алертинг.

### Основные возможности

#### 1. **Graph** — построение графиков

Перейди в `Graph` (верхнее меню) для выполнения PromQL запросов.

**Примеры запросов:**

```promql
# Количество ошибок в минуту
sum(rate(log_errors_total[5m]))

# Среднее время выполнения хендлеров
histogram_quantile(0.95, rate(handler_duration_bucket[5m]))

# Uptime бота
time() - process_start_time_seconds{job="vpn-bot"}

# Использование памяти (MB)
process_resident_memory_bytes{job="vpn-bot"} / 1024 / 1024

# Количество активных подключений
sum(handler_active_connections)
```

#### 2. **Alerts** — просмотр алертов

Перейди в `Alerts` для просмотра активных алертов.

**Статусы алертов:**
- 🔴 **FIRING** — алерт активен
- 🟡 **PENDING** — ожидание подтверждения (for: 2m)
- 🟢 **INACTIVE** — алерт не активен

**Примеры алертов:**
- `HighErrorRate` — >10 ошибок/мин
- `CriticalErrorsDetected` — CRITICAL ошибки
- `BotDown` — бот недоступен

#### 3. **Targets** — проверка источников метрик

Перейди в `Status → Targets` для проверки статуса scrape targets.

**Статусы:**
- ✅ **UP** — источник доступен
- ❌ **DOWN** — источник недоступен

#### 4. **Rules** — просмотр правил алертов

Перейди в `Status → Rules` для просмотра правил из `alerts.yml`.

---

## 📈 Grafana (http://localhost:3001)

### Назначение
Визуализация метрик и логов, дашборды.

### Первый вход

1. Открой http://localhost:3001
2. Логин: `admin`
3. Пароль: `admin`
4. Смени пароль при первом входе

### Добавление источников данных

#### 1. **Добавить Prometheus**

```
Configuration → Data sources → Add data source → Prometheus
URL: http://localhost:9092
Save & test
```

#### 2. **Добавить Loki**

```
Configuration → Data sources → Add data source → Loki
URL: http://localhost:3100
Save & test
```

#### 3. **Добавить Tempo**

```
Configuration → Data sources → Add data source → Tempo
URL: http://localhost:3200
Save & test
```

### Создание дашборда

#### 1. **Дашборд метрик**

```
Create → Dashboard → Add new panel
```

**Примеры панелей:**

**Ошибка в минуту:**
- Title: `Error Rate`
- Query: `sum(rate(log_errors_total[5m]))`
- Visualization: `Time series`

**Использование памяти:**
- Title: `Memory Usage`
- Query: `process_resident_memory_bytes{job="vpn-bot"} / 1024 / 1024`
- Visualization: `Gauge`

**Время выполнения хендлеров:**
- Title: `Handler Latency (p95)`
- Query: `histogram_quantile(0.95, rate(handler_duration_bucket[5m]))`
- Visualization: `Time series`

#### 2. **Дашборд логов (Loki)**

```
Create → Dashboard → Add new panel → Choose visualization: Logs
Data source: Loki
```

**LogQL запросы:**

```logql
# Все ошибки за последние 5 минут
{level="ERROR"} |= `` | line_format `{{.message}}`

# Ошибки с конкретным trace_id
{trace_id="a1b2c3d4"}

# Логи конкретного пользователя
{user_id="123"}

# Медленные запросы к БД
{level="WARNING"} |= "Slow database query"
```

#### 3. **Дашборд трассировок (Tempo)**

```
Create → Dashboard → Add new panel → Choose visualization: Table
Data source: Tempo
```

**Поля для отображения:**
- `Trace ID`
- `Service Name`
- `Operation Name`
- `Duration`
- `Start Time`

---

## 🗄️ Loki (http://localhost:3100)

### Назначение
Агрегация и хранение логов.

### API endpoints

#### 1. **Получить логи**

```bash
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={level="ERROR"}' \
  --data-urlencode 'start=2026-03-31T00:00:00Z' \
  --data-urlencode 'end=2026-03-31T23:59:59Z' \
  --data-urlencode 'limit=100'
```

#### 2. **Получить метки (labels)**

```bash
curl "http://localhost:3100/loki/api/v1/labels"
```

#### 3. **Получить значения метки**

```bash
curl "http://localhost:3100/loki/api/v1/label/level/values"
curl "http://localhost:3100/loki/api/v1/label/trace_id/values"
```

### LogQL шпаргалка

```logql
# Фильтрация по меткам
{job="bot_3xui", level="ERROR"}

# Поиск по тексту
{job="bot_3xui"} |= "payment"

# Отрицание
{job="bot_3xui"} !|= "debug"

# Регулярные выражения
{job="bot_3xui"} |~ "error.*database"

# Извлечение полей
{job="bot_3xui"} | json | user_id="123"

# Форматирование вывода
{job="bot_3xui"} | line_format `{{.timestamp}} {{.level}} {{.message}}`

# Агрегация
sum(rate({job="bot_3xui"} |= "error"[5m]))

# Поиск по trace_id
{trace_id="a1b2c3d4"} | json

# Все логи пользователя
{user_id="123"} | json

# Ошибки по типу
{error_type="ConnectionError"} | json
```

### Примеры использования

#### 1. **Найти все логи по trace_id**

```logql
{trace_id="a1b2c3d4"}
```

#### 2. **Найти ошибки конкретного пользователя**

```logql
{user_id="123", level="ERROR"}
```

#### 3. **Найти медленные запросы**

```logql
{level="WARNING"} |= "Slow database query"
```

#### 4. **Посчитать количество ошибок по типам**

```logql
sum by (error_type) (rate({level="ERROR"}[5m]))
```

---

## 🕵️ Tempo (http://localhost:3200)

### Назначение
Хранение и поиск распределённых трассировок.

### API endpoints

#### 1. **Поиск трассировок**

```bash
curl -G "http://localhost:3200/api/search" \
  --data-urlencode 'q={ .service.name = "bot_3xui" }' \
  --data-urlencode 'tags={"error":"true"}' \
  --data-urlencode 'limit=20'
```

#### 2. **Получить трассировку по ID**

```bash
curl "http://localhost:3200/api/traces/a1b2c3d4"
```

#### 3. **Получить сервисы**

```bash
curl "http://localhost:3200/api/echo/services"
```

### Поиск трассировок в Grafana

1. Открой `Explore` (левое меню)
2. Выбери источник данных: **Tempo**
3. Введи `trace_id` в поле поиска
4. Нажми `Run query`

### Примеры использования

#### 1. **Найти трассировку по ID**

```
Trace ID: a1b2c3d4
```

#### 2. **Найти все трассировки с ошибками**

```
Tags: {error="true"}
Service: bot_3xui
Limit: 20
```

#### 3. **Анализ трассировки**

Открой трассировку в Grafana для просмотра:
- **Waterfall view** — визуализация временной шкалы
- **Span details** — детали каждого спана
- **Process tree** — дерево вызовов

---

## 🔗 Связывание данных между сервисами

### 1. **Из Grafana в Loki**

1. Открой дашборд с метриками
2. Кликни на точку на графике (пик ошибок)
3. Выбери `Go to Explore → Logs`
4. Автоматически применится фильтр по времени

### 2. **Из метрик в трассировки**

1. Найди алерт о высокой задержке
2. Скопируй `trace_id` из логов
3. Открой `Explore → Tempo`
4. Вставь `trace_id` для просмотра трассировки

### 3. **Полный цикл отладки**

```
1. Prometheus: Алерт "HighErrorRate"
   ↓
2. Grafana: Дашборд с ошибками
   ↓
3. Loki: Логи с trace_id="abc123"
   ↓
4. Tempo: Трассировка trace_id="abc123"
   ↓
5. Находим проблемный сервис
```

---

## 🎯 Типичные сценарии

### Сценарий 1: Расследование инцидента

```
1. Получил алерт в Telegram (HighErrorRate)
   ↓
2. Открыл Grafana Alerts → Проверил статус
   ↓
3. Перешёл в Explore → Loki
   ↓
4. Нашёл логи с error_type="DatabaseError"
   ↓
5. Скопировал trace_id
   ↓
6. Открыл Tempo → Нашёл полную трассировку
   ↓
7. Определил корневую причину
```

### Сценарий 2: Поиск медленных запросов

```
1. Prometheus → Query: sum(rate(slow_queries_total[5m]))
   ↓
2. Grafana → Выбрал пик на графике
   ↓
3. Клик → Go to Explore → Logs
   ↓
4. Loki → Фильтр: |= "Slow database query"
   ↓
5. Нашёл конкретные запросы
   ↓
6. Оптимизировал SQL
```

### Сценарий 3: Отладка пользователя

```
1. Пользователь пожаловался на ошибку
   ↓
2. Loki → {user_id="123"} | json
   ↓
3. Нашёл все логи пользователя
   ↓
4. Увидел trace_id="xyz789"
   ↓
5. Tempo → trace_id="xyz789"
   ↓
6. Просмотрел полный путь запроса
   ↓
7. Нашёл проблему в XUI API
```

---

## 🛠️ Полезные команды

### Prometheus

```bash
# Проверка статуса
curl http://localhost:9092/-/healthy

# Reload конфигурации
curl -X POST http://localhost:9092/-/reload

# Метрики самого Prometheus
curl http://localhost:9092/metrics
```

### Loki

```bash
# Проверка статуса
curl http://localhost:3100/ready

# Статистика
curl http://localhost:3100/loki/api/v1/index/stats
```

### Tempo

```bash
# Проверка статуса
curl http://localhost:3200/ready

# Метрики
curl http://localhost:3200/metrics
```

### Grafana

```bash
# Проверка статуса
curl http://localhost:3001/api/health

# Версия
curl http://localhost:3001/api/frontend/settings
```

---

## 📚 Дополнительные ресурсы

- **Prometheus:** https://prometheus.io/docs/
- **Grafana:** https://grafana.com/docs/
- **Loki:** https://grafana.com/docs/loki/latest/
- **Tempo:** https://grafana.com/docs/tempo/latest/
- **LogQL:** https://grafana.com/docs/loki/latest/logql/
- **PromQL:** https://prometheus.io/docs/prometheus/latest/querying/basics/

---

## 🆘 Troubleshooting

### Проблема: Prometheus не видит метрики

**Решение:**
```bash
# Проверь target
curl http://localhost:9092/api/v1/targets

# Проверь приложение
curl http://localhost:9101/metrics
```

### Проблема: Loki не получает логи

**Решение:**
```bash
# Проверь Promtail
docker-compose -f docker-compose.monitoring.yml logs promtail

# Проверь позиции
cat /tmp/positions.yaml

# Перезапусти Promtail
docker-compose -f docker-compose.monitoring.yml restart promtail
```

### Проблема: Tempo не показывает трассировки

**Решение:**
```bash
# Проверь экспорт трассировок из приложения
# Убедись, что OpenTelemetry Collector запущен
docker-compose -f docker-compose.monitoring.yml ps otel-collector

# Проверь логи OTEL
docker-compose -f docker-compose.monitoring.yml logs otel-collector
```

### Проблема: Grafana не подключается к источникам

**Решение:**
```bash
# Проверь network_mode в docker-compose
# Все сервисы должны использовать network_mode: host

# Или используй внутренние URL
Prometheus: http://prometheus:9092
Loki: http://loki:3100
Tempo: http://tempo:3200
```
