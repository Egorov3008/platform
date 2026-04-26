# 🔧 Исправление проблем стабильности бота

## 📋 Выявленные проблемы

### 1. Нехватка памяти
- Система: 1.9GB RAM, свободно только 159MB
- Swap активен (213MB из 512MB)
- Бот потребляет значительную часть памяти

### 2. Частые перезапуски сервиса
За последние 24 часа сервис перезапускался **12+ раз**:
- Много `SIGTERM` сигналов
- В 14:52:12 — `Killing process with signal SIGKILL` (процесс убивался системой)

### 3. Сетевые таймауты Telegram
```
Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error
```

### 4. Дублирование ключей в БД
```
duplicate key value violates unique constraint "keys_pkey"
DETAIL: Key (tg_id, client_id)=(...) already exists.
```

---

## ✅ Выполненные исправления

### 1. Оптимизация systemd (`bot.service`)

**Файл:** `/home/tds_admin/Bot_3xui_vpn/bot.service`

Добавлено:
- `TimeoutStartSec=60` — таймаут запуска
- `TimeoutStopSec=30` — таймаут остановки
- `WatchdogSec=120` — автоматический перезапуск при зависании
- `MemoryLimit=1G` — ограничение памяти
- `MemoryHigh=800M` — предупреждение о высоком потреблении
- `RestartSteps=5`, `RestartMaxDelay=60` — экспоненциальная задержка перезапуска

**Установка:**
```bash
sudo cp /home/tds_admin/Bot_3xui_vpn/bot.service /etc/systemd/system/bot.service
sudo systemctl daemon-reload
```

### 2. Обработка ошибок Telegram (`main.py`)

Добавлена детальная обработка исключений:
- `TelegramRetryAfter` — flood control, ожидание указанное время
- `TelegramAPIError` — другие ошибки API
- `TelegramNetworkError` — сетевые ошибки
- `asyncio.CancelledError` — graceful shutdown

### 3. Исправление гонки при обновлении ключей (`database/base.py`)

Для таблицы `keys` теперь используется `UPSERT`:
```sql
INSERT INTO keys (...)
ON CONFLICT (tg_id, client_id) DO UPDATE SET ...
```

Это предотвращает ошибку дублирования при параллельных запросах.

### 4. Мониторинг ресурсов (`main.py`)

Добавлена функция `monitor_resources()`:
- Логирует потребление памяти каждые 5 минут
- Предупреждения при >80% памяти
- Критические алерты при >90%

**Требуется установка:**
```bash
source /home/tds_admin/Bot_3xui_vpn/venv/bin/activate
pip install psutil==7.1.0
```

### 5. Watchdog сервис (`main.py`)

Интеграция с systemd watchdog:
- Отправка heartbeat каждые 30 секунд
- Автоматический перезапуск если бот не отвечает 2 минуты

---

## 🚀 Инструкция по применению

### Шаг 1: Установка зависимостей
```bash
cd /home/tds_admin/Bot_3xui_vpn
source venv/bin/activate
pip install -r requirements.txt
```

### Шаг 2: Обновление конфигурации systemd
```bash
sudo cp bot.service /etc/systemd/system/bot.service
sudo systemctl daemon-reload
```

### Шаг 3: Перезапуск бота
```bash
sudo systemctl restart bot.service
```

### Шаг 4: Проверка статуса
```bash
# Текущий статус
systemctl status bot.service

# Логи в реальном времени
journalctl -u bot.service -f

# Проверка памяти
systemctl show bot.service | grep Memory
```

---

## 📊 Мониторинг

### Полезные команды

```bash
# Статистика перезапусков
journalctl -u bot.service | grep -E "(Started|Stopped|Restarted)"

# Ошибки за последний час
journalctl -u bot.service --since "1 hour ago" -p 3

# Потребление памяти
systemctl status bot.service | grep Memory

# Время работы
systemctl show -p ExecMainStartTimestamp bot.service
```

### Логи

- **Основной лог:** `/home/tds_admin/Bot_3xui_vpn/logs/application.log`
- **Ошибки:** `/home/tds_admin/Bot_3xui_vpn/logs_error/errors.log`

---

## ⚠️ Рекомендации

### 1. Увеличьте RAM (если возможно)
Текущие 1.9GB — критически мало. Рекомендуется 4GB+.

### 2. Настройте swap
```bash
# Проверка swap
free -h

# Если swap < 1GB, рекомендуется увеличить
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 3. Оптимизируйте кэш
Если проблема с памятью продолжится:
- Уменьшите размер кеша в Redis
- Настройте TTL для кеша
- Рассмотрите использование LRU eviction

### 4. Мониторинг в реальном времени
```bash
# Установите htop
sudo apt install htop

# Запустите мониторинг процесса
htop -p $(systemctl show bot.service --value -p MainPID)
```

---

## 📈 Метрики для наблюдения

1. **Memory usage** — должно быть <80%
2. **Restart count** — не более 1-2 в сутки
3. **Response time** — обработка callback <500ms
4. **Cache hit rate** — >90%

---

## 🆘 Если бот продолжает падать

1. Проверьте логи:
   ```bash
   journalctl -u bot.service --since "30 minutes ago" --no-pager
   ```

2. Проверьте память:
   ```bash
   free -h && df -h /
   ```

3. Проверьте БД:
   ```bash
   psql $DATABASE_URL -c "SELECT count(*) FROM keys;"
   ```

4. Перезапустите с очисткой кеша:
   ```bash
   sudo systemctl stop bot.service
   redis-cli FLUSHDB
   sudo systemctl start bot.service
   ```
