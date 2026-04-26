# 🔍 Анализ утечки памяти

## 📊 Текущее состояние

На момент последнего запуска:
- **Бот:** 128 MB RSS (6.9% памяти)
- **Система:** 1.9 GB total, 377 MB available (80.4% использовано)
- **Swap:** 249 MB из 512 MB (48%)

---

## 🛠️ Инструменты для анализа

### 1. Быстрая проверка (production)

```bash
# Текущее потребление памяти ботом
systemctl status bot.service | grep Memory

# Детальная статистика
systemctl show bot.service | grep -E "(Memory|Tasks)"

# Процесс и память
ps aux | grep "python3.*main.py" | grep -v grep

# Логи мониторинга (каждые 5 мин)
journalctl -u bot.service | grep "Мониторинг ресурсов" | tail -20
```

### 2. Непрерывный мониторинг

**Запуск мониторинга:**
```bash
cd /home/tds_admin/Bot_3xui_vpn
source venv/bin/activate
python3 memory_monitor.py
```

**Анализ накопленных данных:**
```bash
python3 memory_monitor.py analyze
```

**Результаты сохраняются в:** `memory_monitor.csv`

### 3. Глубокий анализ утечек

**Запуск анализатора:**
```bash
cd /home/tds_admin/Bot_3xui_vpn
source venv/bin/activate
python3 analyze_memory_leak.py
```

**Что проверяет:**
- Распределение объектов по типам
- Сборщик мусора (поколения 0, 1, 2)
- Асинхронные задачи
- Объекты кеша
- Тренд потребления (3 снимка)

---

## 📈 Признаки утечки памяти

### Критерии обнаружения:

| Показатель | Норма | Тревога | Критично |
|------------|-------|---------|----------|
| RSS бота | <200 MB | >400 MB | >800 MB |
| % памяти бота | <10% | >30% | >50% |
| System available | >500 MB | <200 MB | <100 MB |
| Swap used | <20% | >50% | >80% |
| Рост RSS/час | <50 MB | >100 MB | >200 MB |

### Как определить утечку:

1. **Запустите мониторинг на 1-2 часа:**
   ```bash
   python3 memory_monitor.py &
   ```

2. **Проверьте тренд:**
   ```bash
   python3 memory_monitor.py analyze
   ```

3. **Если рост >100 MB/час — вероятна утечка**

---

## 🔬 Типичные причины утечек в Python

### 1. Не закрытые соединения

```python
# ❌ ПЛОХО
session = aiohttp.ClientSession()
data = await session.get(url)
# session не закрыт!

# ✅ ХОРОШО
async with aiohttp.ClientSession() as session:
    data = await session.get(url)
```

### 2. Глобальные списки/кеш без ограничения

```python
# ❌ ПЛОХО
cache = []
def add(data):
    cache.append(data)  # Растёт бесконечно

# ✅ ХОРОШО
from cachetools import LRUCache
cache = LRUCache(maxsize=1000)
```

### 3. Циклические ссылки

```python
# ❌ ПЛОХО
class A:
    def __init__(self):
        self.b = B(self)

class B:
    def __init__(self, a):
        self.a = a  # Циклическая ссылка

# ✅ ХОРОШО
import weakref

class A:
    def __init__(self):
        self.b = B(weakref.ref(self))

class B:
    def __init__(self, a_ref):
        self.a = a_ref()  # Слабая ссылка
```

### 4. Забытые asyncio задачи

```python
# ❌ ПЛОХО
async def start():
    asyncio.create_task(background_worker())  # Забыли сохранить

# ✅ ХОРОШО
tasks = set()
async def start():
    task = asyncio.create_task(background_worker())
    tasks.add(task)
    task.add_done_callback(tasks.discard)
```

---

## 🧭 План диагностики

### Шаг 1: Быстрая оценка (5 мин)

```bash
# Проверка текущего состояния
systemctl status bot.service

# Проверка логов на ошибки памяти
journalctl -u bot.service --since "1 hour ago" | grep -i "memory\|память"
```

### Шаг 2: Мониторинг (1-2 часа)

```bash
# Запуск в фоне
nohup python3 memory_monitor.py > memory_log.txt 2>&1 &
echo $!  # Запомните PID для остановки
```

### Шаг 3: Анализ тренда

```bash
# После 1-2 часов мониторинга
python3 memory_monitor.py analyze

# Смотрим на тренд
# Если рост >100 MB/час → переходим к шагу 4
```

### Шаг 4: Глубокий анализ

```bash
# Останавливаем бота
sudo systemctl stop bot.service

# Запускаем анализатор
python3 analyze_memory_leak.py

# Ищем в выводе:
# - Какие типы объектов растут?
# - Какие строки кода потребляют больше всего?
```

### Шаг 5: Профилирование в production

```bash
# Установите memory_profiler
pip install memory_profiler

# Добавьте в main.py перед подозрительным кодом:
from memory_profiler import profile

@profile
def suspicious_function():
    ...

# Запустите бота и смотрите вывод
```

---

## 📊 Анализ через tracemalloc

Добавьте в начало `main.py`:

```python
import tracemalloc
tracemalloc.start(25)  # 25 уровней стека

# В любом месте для проверки:
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)
```

---

## 🔧 Оптимизации для текущего проекта

### 1. Ограничение размера кеша

Проверьте `services/cache/service.py`:

```python
# Добавьте ограничение
MAX_CACHE_SIZE = 10000  # максимум объектов на модель
```

### 2. TTL для кеша

```python
# Установите время жизни кеша
CACHE_TTL = 3600  # 1 час
```

### 3. Принудительная сборка мусора

Добавьте в `monitor_resources()`:

```python
import gc

# Каждые 30 минут
if int(time.time()) % 1800 < 300:
    gc.collect()
    logger.info("Принудительная сборка мусора")
```

---

## 📋 Чеклист проверки

- [ ] Запущен `memory_monitor.py` (1-2 часа)
- [ ] Проверен тренд потребления
- [ ] Проверены логи на ошибки памяти
- [ ] Проверен размер кеша
- [ ] Проверены активные asyncio задачи
- [ ] Проверены соединения с БД (пул)
- [ ] Проверены соединения с Telegram API

---

## 🆘 Если утечка подтверждена

1. **Временно:** Перезапуск бота по расписанию
   ```bash
   # В systemd таймер или cron
   0 4 * * * systemctl restart bot.service
   ```

2. **Найти источник:** Использовать `analyze_memory_leak.py`

3. **Исправить:** Закрыть соединения, ограничить кеш

4. **Верифицировать:** Запустить мониторинг снова

---

## 📞 Полезные команды

```bash
# График потребления (если установлен gnuplot)
gnuplot -e "set terminal png; set output 'memory.png'; \
            set xdata time; set timefmt '%Y-%m-%dT%H:%M:%S'; \
            set format x '%H:%M'; plot 'memory_monitor.csv' \
            using 1:3 with lines title 'RSS MB'"

# Очистка старого лога
> memory_monitor.csv

# Экспорт статистики за период
grep "2026-03-28" memory_monitor.csv > daily_stats.csv
```
