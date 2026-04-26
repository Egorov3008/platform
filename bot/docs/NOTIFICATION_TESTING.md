# Модуль уведомлений — Руководство по тестированию

## 📋 Обзор модуля

Система уведомлений состоит из **4 воронок** (funnels), управляемых `FunnelManager`:

### Воронки

| Воронка | ID | Тип | Триггер | Cooldown |
|--------|----|----|---------|------------|
| **Истечение ключа** | `key_expiry_24h` | По ключам | Ключ истекает через 24ч | 25ч |
| **Напоминание о пробном периоде** | `trial_unused` | По ключам | Пробный ключ с 0 ГБ трафика | 3 дня |
| **Холодные лиды** | `cold_lead` | По пользователям | Зарегистрирован >15 дней, нет пробного | 15 дней |
| **Бонус за реферала** | `referral_bonus` | По пользователям | Приглашённый пользователь, нет пробного | 30 дней |

---

## 🔍 Условия отправки уведомлений

### 1. **Воронка истечения ключа** (`key_expiry_24h`)

**Условия триггера:**
- Сегмент ключа = `KeySegment.EXPIRING_24H` (истекает через 24ч)
- Флаг ключа `notified_24h` = `False`
- Кэш дедупликации = miss (или истёк)

**Сообщение:** Показывает оставшиеся часы, email, время истечения и кнопку "Продлить ключ"

**Дедупликация:**
- Область: `key_expiry_24h:{key.email}`
- Длительность: 25 часов (предотвращает повторное уведомление в последний день)

**Обновление БД:**
```sql
UPDATE keys SET notified_24h = TRUE WHERE email = '{key.email}'
```

---

### 2. **Воронка напоминания о пробном периоде** (`trial_unused`)

**Условия триггера:**
- Сегмент ключа = `KeySegment.TRIAL` (tariff_id == 10)
- Использованный трафик = 0.0 ГБ (ключ не подключен)
- Кэш дедупликации = miss (или истёк через 3 дня)

**Сообщение:** Побуждает пользователя подключиться к пробной VPN

**Дедупликация:**
- Область: `trial_unused` (по пользователю, без гранулярности по ключам)
- Длительность: 3 дня

**Обновление БД:** Отсутствует — только дедупликация

---

### 3. **Воронка холодных лидов** (`cold_lead`)

**Условия триггера:**
- `user.trial` = 0 (нет активированного пробного периода)
- `user.keys` = пусто (нет платных ключей)
- Аккаунт зарегистрирован более 15 дней назад
- Кэш дедупликации = miss (или истёк через 15 дней)

**Сообщение:** Промо-сообщение для активации бесплатного пробного периода

**Дедупликация:**
- Область: `cold_lead` (по пользователю)
- Длительность: 15 дней

**Обновление БД:** Отсутствует — только дедупликация

---

### 4. **Воронка бонуса за реферала** (`referral_bonus`)

**Условия триггера:**
- `user.referral_id` ≠ NULL (пользователь приглашён другом)
- `user.trial` = 0 (пробный период ещё не активирован)
- `user.keys` = пусто (нет платных ключей)
- Кэш дедупликации = miss (или истёк через 30 дней)

**Сообщение:** Приветственное сообщение для приглашённого пользователя

**Дедупликация:**
- Область: `referral_bonus` (по пользователю)
- Длительность: 30 дней

**Обновление БД:** Отсутствует — только дедупликация

---

## 🕐 Ограничения выполнения

**Временное окно отправки:** 9:00 — 22:59 (локальное серверное время)
- За пределами этого окна: цикл пропускается

**Ограничение скорости:**
- Глобальное: 25 сообщений/сек
- Per-user: минимум 1.1 сек между сообщениями одному пользователю
- Повтор: Одна автоматическая попытка при flood control (TelegramRetryAfter)

**Частота цикла:** Каждый 1 час (настраивается в фоновых задачах)

---

## 📊 Сценарии тестирования

### Сценарий 1: Уведомление об истечении ключа

**Начальные условия:**
```
Пользователь (tg_id=123):
  - trial: любое значение
  - blocked: False

Ключ (email=user@example.com):
  - tg_id: 123
  - tariff_id: 20 (платный)
  - expiry_time: NOW + 12 часов
  - total_gb: 100.0 (неиспользованный)
  - notified_24h: False ✓

Состояние кэша/БД:
  - Ключ в кэше
  - Ключ в БД
  - Кэш дедупликации пуст для "key_expiry_24h:user@example.com"
```

**Ожидаемое поведение:**
1. ✅ KeySegmentation определяет ключ как `EXPIRING_24H`
2. ✅ FunnelManager передаёт segment_keys в KeyExpiryFunnel
3. ✅ Воронка проверяет `should_send(ctx)` → True (segment_keys не пусто)
4. ✅ Проверяет флаг `notified_24h` → False
5. ✅ Проверяет кэш дедупликации → miss
6. ✅ Отправляет сообщение с кнопкой "Продлить ключ"
7. ✅ Обновляет `keys.notified_24h = True` в БД
8. ✅ Устанавливает кэш дедупликации с TTL 25ч
9. ✅ Результат: `sent=1, skipped=0, failed=0`

**Проверка:**
```bash
# Проверить уведомление в кэше после выполнения
SELECT notified_24h FROM keys WHERE email = 'user@example.com';
# Ожидается: True

# Проверить логи
grep "Цикл уведомлений завершён" logs/application.log
# Ожидается: results_by_funnel: {'key_expiry_24h': {'sent': 1, ...}}
```

---

### Сценарий 2: Напоминание о пробном периоде (Неиспользуемый ключ)

**Начальные условия:**
```
Пользователь (tg_id=456):
  - trial: 1 (пробный период активирован)
  - blocked: False

Ключ (email=trial@example.com):
  - tg_id: 456
  - tariff_id: 10 (пробный)
  - created_at: NOW - 3 дня
  - used_traffic: 0.0 ✓ (не подключен)
  - expiry_time: NOW + 7 дней (ещё действует)

Состояние кэша/БД:
  - Кэш дедупликации пуст для "trial_unused" + tg_id 456
```

**Ожидаемое поведение:**
1. ✅ KeySegmentation определяет ключ как `TRIAL` (tariff_id == 10)
2. ✅ FunnelManager передаёт ключ в TrialReminderFunnel
3. ✅ Проверяет `should_send(ctx)` → True (найден неиспользуемый пробный ключ)
4. ✅ Проверяет кэш дедупликации → miss
5. ✅ Отправляет сообщение "Попробуйте подключиться к VPN"
6. ✅ Устанавливает кэш дедупликации с TTL 3 дня
7. ✅ **НЕ обновляет БД** (только кэш дедупликации)
8. ✅ Результат: `sent=1, skipped=0, failed=0`

**Проверка:**
```bash
# Ожидается отсутствие обновления БД
SELECT used_traffic FROM keys WHERE email = 'trial@example.com';
# Ожидается: 0.0 (без изменений)

# Проверить логи
grep "trial_unused" logs/application.log | grep "sent"
```

---

### Сценарий 3: Холодный лид (Старая регистрация, никогда не пробовал)

**Начальные условия:**
```
Пользователь (tg_id=789):
  - trial: 0 ✓ (никогда не активировал)
  - created_at: NOW - 45 дней ✓ (старая регистрация)
  - blocked: False
  - keys: [] ✓ (нет ключей)

Состояние кэша/БД:
  - Пользователь в кэше
  - Кэш дедупликации пуст для "cold_lead" + tg_id 789
```

**Ожидаемое поведение:**
1. ✅ UserSegmenter определяет сегмент как `COLD_LEAD`
2. ✅ ColdLeadFunnel проверяет `should_send(ctx)`:
   - `user.trial == 0` → True
   - `user.keys` пусто → True
   - Дедупликация miss → True
3. ✅ Отправляет промо-сообщение "Активировать пробный период"
4. ✅ Устанавливает кэш дедупликации с TTL 15 дней
5. ✅ Результат: `sent=1, failed=0`

**Проверка:**
```bash
# Проверить логи
grep "cold_lead" logs/application.log | grep sent
# Ожидается: sent=1
```

---

### Сценарий 4: Бонус за реферала (Приглашённый пользователь)

**Начальные условия:**
```
Пользователь (tg_id=999):
  - referral_id: 123 ✓ (приглашён пользователем 123)
  - trial: 0 ✓ (не активирован)
  - blocked: False
  - keys: [] ✓ (нет ключей)

Состояние кэша/БД:
  - Пользователь в кэше с установленным referral_id
  - Кэш дедупликации пуст для "referral_bonus" + tg_id 999
```

**Ожидаемое поведение:**
1. ✅ ReferralBonusFunnel проверяет `should_send(ctx)`:
   - `user.referral_id != None` → True
   - `user.trial == 0` → True
   - Дедупликация miss → True
2. ✅ Отправляет сообщение "Добро пожаловать через реферала"
3. ✅ Устанавливает кэш дедупликации с TTL 30 дней
4. ✅ Результат: `sent=1, failed=0`

---

### Сценарий 5: Кэш дедупликации предотвращает повторное уведомление

**Начальные условия:**
```
То же, что сценарий 1, но:
  - Кэш дедупликации: УЖЕ УСТАНОВЛЕН для "key_expiry_24h:user@example.com"
  - TTL: осталось 10 часов

Ключ:
  - notified_24h: True (уже уведомлён)
```

**Ожидаемое поведение:**
1. ✅ Сегмент ключа = `EXPIRING_24H` (по-прежнему совпадает)
2. ✅ Проверка флага `notified_24h` → True → ПРОПУСТИТЬ
3. ✅ Проверка кэша дедупликации → HIT → ПРОПУСТИТЬ
4. ✅ Результат: `skipped=1, sent=0`

**Проверка:**
```bash
grep "Ошибка обновления БД" logs/application.log
# Ожидается: НЕТ логов об ошибках
```

---

### Сценарий 6: Пользователь заблокировал бота

**Начальные условия:**
```
Пользователь (tg_id=111):
  - blocked: False (ещё не отмечен как заблокировавший)
  - Ключи истекают через 24ч

Но при попытке отправки:
  - Пользователь блокирует бота
  - Выбрасывается TelegramForbiddenError
```

**Ожидаемое поведение:**
1. ✅ RateLimiter перехватывает `TelegramForbiddenError`
2. ✅ Логирует "Пользователь заблокировал бота"
3. ✅ Возвращает `"blocked"` → NotificationResult.failed_blocked += 1
4. ✅ Результат: `sent=0, failed_blocked=1, failed_other=0`

**Замечание:** Пользователь НЕ автоматически отмечается как `is_blocked=True` в этом модуле. Администратор должен обновить вручную, если необходимо.

**Проверка:**
```bash
grep "Пользователь заблокировал бота" logs/application.log
# Ожидается: tg_id=111
```

---

### Сценарий 7: Превышен лимит скорости

**Начальные условия:**
```
- Пакет из 50 уведомлений для отправки
- Глобальная скорость: 25 сообщений/сек
- Per-user: минимум 1.1 сек
```

**Ожидаемое поведение:**
1. ✅ RateLimiter активирует token-bucket
2. ✅ Первые 25 сообщений отправлены сразу
3. ✅ Остальные 25: throttled со скоростью ~1/сек (ещё 40 секунд)
4. ✅ Общая длительность цикла: ~42 секунды вместо мгновенной
5. ✅ Никакие сообщения не потеряны, все успешно отправлены

**Проверка:**
```bash
grep "Цикл уведомлений завершён" logs/application.log
# Ожидается: duration: "42.5s"
```

---

### Сценарий 8: За пределами временного окна отправки

**Начальные условия:**
```
- Текущее время: 23:30 (за пределами окна 9:00-23:00)
- Множество уведомлений ожидают отправки
```

**Ожидаемое поведение:**
1. ✅ FunnelManager.run_cycle() проверяет `_in_sending_window()`
2. ✅ Возвращает False
3. ✅ Логирует "Уведомления: нерабочее время, пропуск цикла"
4. ✅ Никакие уведомления не отправлены
5. ✅ Возвращает пустой FunnelRunReport

**Проверка:**
```bash
grep "нерабочее время, пропуск цикла" logs/application.log
```

---

## 🛠️ Подготовка к живому тестированию

### 1. **Подготовка БД**

```sql
-- Проверить статусы ключей
SELECT email, tg_id, tariff_id, expiry_time, notified_24h, created_at
FROM keys
LIMIT 20;

-- Отметить ключи как неуведомлённые (сброс для тестирования)
UPDATE keys
SET notified_24h = FALSE
WHERE tariff_id IN (20, 25, 30) AND notified_24h = TRUE;

-- Проверить использование пробных ключей
SELECT email, tg_id, tariff_id, used_traffic, total_gb, created_at
FROM keys
WHERE tariff_id = 10
LIMIT 10;

-- Проверить статус пользователей
SELECT tg_id, trial, created_at, is_blocked, referral_id
FROM users
LIMIT 20;
```

### 2. **Создание тестовых пользователей**

```python
# Создать тестовых пользователей с разными сценариями

# Холодный лид (зарегистрирован 30+ дней назад, без пробного)
cold_lead_user = User(
    tg_id=999001,
    trial=0,
    is_blocked=False,
    created_at=datetime.now() - timedelta(days=40),
    referral_id=None
)

# Реферальный пользователь
referral_user = User(
    tg_id=999002,
    trial=0,
    is_blocked=False,
    created_at=datetime.now() - timedelta(days=5),
    referral_id=123456
)

# Пробный пользователь с неиспользуемым ключом
trial_user = User(
    tg_id=999003,
    trial=1,
    is_blocked=False,
    created_at=datetime.now() - timedelta(days=3)
)

# Создать пробный ключ (неиспользуемый)
trial_key = Key(
    email="test.trial@example.com",
    tg_id=999003,
    tariff_id=10,
    created_at=int((datetime.now() - timedelta(days=3)).timestamp() * 1000),
    expiry_time=int((datetime.now() + timedelta(days=7)).timestamp() * 1000),
    used_traffic=0.0,
    total_gb=10.0,
    notified_24h=False
)
```

### 3. **Подготовка кэша**

Перед тестированием убедитесь, что кэш заполнен:

```python
# В setup тестирования
await cache_service.users.set(cache_keys.user(cold_lead_user.tg_id), cold_lead_user)
await cache_service.users.set(cache_keys.user(referral_user.tg_id), referral_user)
await cache_service.users.set(cache_keys.user(trial_user.tg_id), trial_user)

await cache_service.keys.set(cache_keys.key(trial_key.email), trial_key)
```

### 4. **Создание истекающих ключей для тестирования**

```sql
-- Создать ключ, истекающий через 12 часов
INSERT INTO keys (
    email, tg_id, tariff_id, created_at, expiry_time,
    total_gb, used_traffic, notified_24h
) VALUES (
    'expiring.test@example.com',
    999004,
    25,
    {current_ms},
    {now_ms + 12 * 3600 * 1000},
    100.0, 0.0, FALSE
);
```

### 5. **Сброс кэша дедупликации**

Перед тестированием очистите кэш дедупликации для повторного тестирования:

```python
# Очистить кэш дедупликации уведомлений
async with cache_service.storage as storage:
    # Очистить весь namespace уведомлений
    # Это позволяет повторно отправлять уведомления для тестирования
    await storage.delete_namespace("notifications")
```

### 6. **Проверка конфигурации**

Проверьте эти параметры в `.env`:

```bash
# Временное окно отправки уведомлений (9:00 - 23:00)
# Для тестирования установите более широкое окно (например, 0-23 для 24-часового окна)
NOTIFICATION_SENDING_WINDOW_START=9
NOTIFICATION_SENDING_WINDOW_END=23

# Режим тестирования (опционально)
# LOG_LEVEL=DEBUG  # Включить debug логи для модуля уведомлений
```

### 7. **Проверка логирования**

Мониторьте эти файлы логов во время тестирования:

```bash
# Главный лог приложения
tail -f logs/application.log | grep -E "(Запуск цикла|Цикл уведомлений|тг_id)"

# Лог ошибок
tail -f logs_error/errors.log

# Мониторинг конкретной воронки
tail -f logs/application.log | grep "key_expiry_24h"
```

---

## 🧪 Рабочий процесс живого тестирования

### Шаг 1: Подготовить тестовые данные
```bash
# Установить тестовых пользователей и ключи, как описано выше
python -c "
import asyncio
from services.cache.service import CacheService
# Вставить тестовые данные здесь
"
```

### Шаг 2: Запустить цикл вручную (опционально)

Если у вас есть обработчик администратора для запуска уведомлений вручную:
```python
# В обработчике администратора или CLI
from services.notification.manager import FunnelManager

manager = FunnelManager(cache, pool)
report = await manager.run_cycle(bot)
print(f"Отчёт: {report}")
```

### Шаг 3: Мониторить выполнение

```bash
# Терминал 1: Мониторить логи
tail -f logs/application.log | grep -E "Цикл|Запуск"

# Терминал 2: Мониторить ошибки
tail -f logs_error/errors.log

# Терминал 3: Проверить изменения БД (если тестируете сценарий 1)
watch -n 5 'psql -c "SELECT email, notified_24h FROM keys WHERE email LIKE \"%.test@%\""'
```

### Шаг 4: Проверить результаты

```bash
# Проверить количество уведомлений
grep "results_by_funnel" logs/application.log | tail -1

# Проверить неудачные попытки
grep -i "failed\|error\|blocked" logs_error/errors.log

# Проверить, что кэш дедупликации установлен
# (потребуется пользовательский запрос или интроспекция кэша)
```

---

## 🐛 Чек-лист отладки

- [ ] **Пользователь не получил уведомление?**
  - Проверить флаг `is_blocked` в таблице users
  - Убедиться, что `tg_id` совпадает между пользователем и ключами
  - Проверить, что кэш содержит актуальные данные user/key
  - Проверить, что не за пределами временного окна (9-23 часов)
  - Проверить задержку rate limiter (1.1 сек на пользователя)

- [ ] **Уведомление отправлено дважды?**
  - Проверить TTL кэша дедупликации (должен предотвратить 2-ю отправку)
  - Проверить флаг `notified_24h` (сценарий key_expiry)
  - Проверить, что кэш не был очищен

- [ ] **БД не обновлена?**
  - Только `key_expiry_24h` обновляет БД (`notified_24h = TRUE`)
  - Другие воронки используют только кэш дедупликации
  - Проверить ошибки подключения к БД в логах

- [ ] **Отправлено неправильное уведомление?**
  - Проверить сегментацию ключей (использовать логи с debug уровнем)
  - Проверить определение сегмента пользователя
  - Проверить маршрутизацию KEY_SEGMENT_TO_FUNNEL

---

## 📈 Тестирование производительности

### Нагрузочное тестирование: 10K пользователей

```python
import asyncio
import time

async def load_test(cache, pool, bot):
    # Создать 10K тестовых пользователей с разными сценариями
    users = []
    keys = []

    # ... генерировать тестовые данные ...

    # Заполнить кэш
    for user in users:
        await cache.users.set(cache_keys.user(user.tg_id), user)
    for key in keys:
        await cache.keys.set(cache_keys.key(key.email), key)

    # Запустить цикл
    manager = FunnelManager(cache, pool)
    start = time.time()
    report = await manager.run_cycle(bot)
    duration = time.time() - start

    print(f"10K пользователей за {duration:.1f}s")
    print(f"Пропускная способность: {len(users) / duration:.0f} пользователей/сек")
    print(f"Отчёт: {report}")
```

**Ожидаемая производительность:**
- ✅ 10K пользователей: <60 секунд
- ✅ Пропускная способность: 150+ пользователей/сек
- ✅ Память стабильна (без утечек)

---

## 📝 Шаблон тестового случая

Используйте этот шаблон для документирования результатов тестирования:

```markdown
### Тест: [Название]

**Дата:** YYYY-MM-DD HH:MM
**Продолжительность:** X секунд

**Подготовка:**
- [Опишите начальные условия]

**Выполнение:**
- [Шаги выполнения]

**Результаты:**
- Уведомлений отправлено: X
- Ошибок (заблокирован): Y
- Ошибок (другие): Z
- Пропущено: W

**Логи:**
```
[Ключевые записи логов]
```

**Проверено:**
- [ ] Содержимое сообщения корректно
- [ ] Кнопки присутствуют
- [ ] БД обновлена (если применимо)
- [ ] Кэш дедупликации установлен (если применимо)
- [ ] Нет дублирующихся отправок
- [ ] Соблюдается ограничение скорости
```

---

## ✅ Чек-лист утверждения

Перед завершением тестирования:

- [ ] Все 4 воронки протестированы (key_expiry, trial_reminder, cold_lead, referral_bonus)
- [ ] Дедупликация кэша проверена для каждой воронки
- [ ] Обновления БД проверены (только key_expiry_24h)
- [ ] Ограничение скорости протестировано с пакетом
- [ ] Временное окно проверено (9-23)
- [ ] Сценарий с заблокированным пользователем обработан
- [ ] TelegramRetryAfter обработан
- [ ] Производительность приемлема (10K пользователей < 60s)
- [ ] Утечек памяти не обнаружено
- [ ] Логи чистые (нет неожиданных ошибок)

---

## 💻 Готовые скрипты для тестирования (копировать в терминал)

### Скрипт 1: Создание тестовых ключей для пользователя 552810834

Копируйте и вставьте в терминал:

```bash
cd /home/claude/bot_3xui && python3 << 'EOF'
import asyncio
import asyncpg
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://claude:7188924Ego@localhost:5432/bot_3xui"

async def create_test_keys():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        tg_id = 552810834
        now_ms = int(datetime.utcnow().timestamp() * 1000)

        print("📌 Создание тестовых ключей для пользователя 552810834...\n")

        # Сценарий 1: Ключ, истекающий через 24 часа
        expiry_24h = now_ms + (24 * 3600 * 1000)
        await conn.execute(
            "DELETE FROM keys WHERE email = $1", "test.expiring.24h@example.com"
        )
        await conn.execute(
            """INSERT INTO keys (tg_id, client_id, email, created_at, expiry_time, key,
               total_gb, inbound_id, notified_24h, notified_10h, tariff_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            tg_id, "test_24h", "test.expiring.24h@example.com", now_ms, expiry_24h,
            "test_key_24h", 100.0, 1, False, False, 20
        )
        print("✅ Сценарий 1: Ключ, истекающий через 24 часа")
        print("   Email: test.expiring.24h@example.com")
        print("   Истекает: " + datetime.utcfromtimestamp(expiry_24h/1000).strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Сценарий 2: Ключ, истекающий через 10 часов
        expiry_10h = now_ms + (10 * 3600 * 1000)
        await conn.execute(
            "DELETE FROM keys WHERE email = $1", "test.expiring.10h@example.com"
        )
        await conn.execute(
            """INSERT INTO keys (tg_id, client_id, email, created_at, expiry_time, key,
               total_gb, inbound_id, notified_24h, notified_10h, tariff_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            tg_id, "test_10h", "test.expiring.10h@example.com", now_ms, expiry_10h,
            "test_key_10h", 100.0, 1, False, False, 25
        )
        print("\n✅ Сценарий 2: Ключ, истекающий через 10 часов")
        print("   Email: test.expiring.10h@example.com")
        print("   Истекает: " + datetime.utcfromtimestamp(expiry_10h/1000).strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Сценарий 3: Пробный ключ, неиспользуемый (0 ГБ трафика)
        trial_expiry = now_ms + (7 * 24 * 3600 * 1000)
        await conn.execute(
            "DELETE FROM keys WHERE email = $1", "test.trial.unused@example.com"
        )
        await conn.execute(
            """INSERT INTO keys (tg_id, client_id, email, created_at, expiry_time, key,
               total_gb, inbound_id, notified_24h, notified_10h, tariff_id, used_traffic)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            tg_id, "test_trial", "test.trial.unused@example.com",
            now_ms - (3 * 24 * 3600 * 1000), trial_expiry,
            "test_key_trial", 10.0, 1, False, False, 10, 0.0
        )
        print("\n✅ Сценарий 3: Пробный ключ, неиспользуемый")
        print("   Email: test.trial.unused@example.com")
        print("   Использовано: 0.0 ГБ")
        print("   Истекает: " + datetime.utcfromtimestamp(trial_expiry/1000).strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Сценарий 4: Активный ключ (>24 часов)
        expiry_active = now_ms + (30 * 24 * 3600 * 1000)
        await conn.execute(
            "DELETE FROM keys WHERE email = $1", "test.active@example.com"
        )
        await conn.execute(
            """INSERT INTO keys (tg_id, client_id, email, created_at, expiry_time, key,
               total_gb, inbound_id, notified_24h, notified_10h, tariff_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            tg_id, "test_active", "test.active@example.com", now_ms, expiry_active,
            "test_key_active", 100.0, 1, False, False, 30
        )
        print("\n✅ Сценарий 4: Активный ключ (без уведомлений)")
        print("   Email: test.active@example.com")
        print("   Истекает: " + datetime.utcfromtimestamp(expiry_active/1000).strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Сценарий 5: Истекший ключ
        expiry_expired = now_ms - (1 * 3600 * 1000)
        await conn.execute(
            "DELETE FROM keys WHERE email = $1", "test.expired@example.com"
        )
        await conn.execute(
            """INSERT INTO keys (tg_id, client_id, email, created_at, expiry_time, key,
               total_gb, inbound_id, notified_24h, notified_10h, tariff_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            tg_id, "test_expired", "test.expired@example.com", now_ms, expiry_expired,
            "test_key_expired", 100.0, 1, True, True, 20
        )
        print("\n✅ Сценарий 5: Истекший ключ")
        print("   Email: test.expired@example.com")
        print("   Истек в: " + datetime.utcfromtimestamp(expiry_expired/1000).strftime("%Y-%m-%d %H:%M:%S UTC"))

        print("\n" + "="*70)
        print("✨ Все тестовые ключи созданы для пользователя 552810834!")
        print("="*70)

    finally:
        await conn.close()

asyncio.run(create_test_keys())
EOF
```

---

### Скрипт 2: Сброс флагов уведомлений для переповторного тестирования

```bash
cd /home/claude/bot_3xui && python3 << 'EOF'
import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://claude:7188924Ego@localhost:5432/bot_3xui"

async def reset_flags():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("🔄 Сброс флагов уведомлений...\n")

        result = await conn.execute(
            """UPDATE keys SET notified_24h = FALSE, notified_10h = FALSE
               WHERE email LIKE 'test.%@example.com' AND tg_id = 552810834"""
        )

        print(f"✅ Сброшены флаги для {result} ключей\n")

        # Показываем новый статус
        keys = await conn.fetch(
            """SELECT email, notified_24h, notified_10h,
                      (expiry_time - EXTRACT(EPOCH FROM NOW()) * 1000)::bigint as ms_left
               FROM keys WHERE email LIKE 'test.%@example.com' AND tg_id = 552810834
               ORDER BY email"""
        )

        print("📊 Статус флагов после сброса:")
        for key in keys:
            hours_left = key['ms_left'] / (3600 * 1000)
            notified = f"24h:{key['notified_24h']}, 10h:{key['notified_10h']}"
            segment = "EXPIRED" if hours_left <= 0 else f"{hours_left:.1f}h"
            print(f"  📧 {key['email']:<35} | {segment:<10} | {notified}")

        print("\n✨ Готово! Флаги сброшены. При следующем цикле будут отправлены уведомления.")

    finally:
        await conn.close()

asyncio.run(reset_flags())
EOF
```

---

### Скрипт 3: Проверка статуса тестовых ключей

```bash
cd /home/claude/bot_3xui && python3 << 'EOF'
import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://claude:7188924Ego@localhost:5432/bot_3xui"

async def check_status():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("🔍 Статус тестовых ключей пользователя 552810834\n")
        print("="*90)

        keys = await conn.fetch(
            """SELECT email, tariff_id, notified_24h, notified_10h,
                      (expiry_time - EXTRACT(EPOCH FROM NOW()) * 1000)::bigint as ms_left,
                      used_traffic, total_gb
               FROM keys WHERE email LIKE 'test.%@example.com' AND tg_id = 552810834
               ORDER BY ms_left DESC"""
        )

        if not keys:
            print("❌ Тестовые ключи не найдены!")
            return

        print(f"{'Email':<35} {'Tariff':<8} {'Hours':<10} {'Segment':<15} {'Flags':<15} {'Traffic':<12}")
        print("-"*90)

        for key in keys:
            hours_left = key['ms_left'] / (3600 * 1000)

            # Определяем сегмент
            if hours_left <= 0:
                segment = "EXPIRED"
                flag = "❌"
            elif key['tariff_id'] == 10:
                segment = "TRIAL"
                traffic = f"{key['used_traffic']:.1f}GB"
                flag = "✓" if key['used_traffic'] == 0 else "✗"
            elif hours_left <= 10:
                segment = "EXPIRING_10H"
                flag = "⚡" if not key['notified_10h'] else "✓"
            elif hours_left <= 24:
                segment = "EXPIRING_24H"
                flag = "⚠️" if not key['notified_24h'] else "✓"
            else:
                segment = "ACTIVE"
                flag = "🟢"

            traffic_str = f"{key['used_traffic']:.1f}/{key['total_gb']:.1f}GB"
            flags = f"24h:{str(key['notified_24h'])[0]}, 10h:{str(key['notified_10h'])[0]}"

            print(f"{key['email']:<35} {key['tariff_id']:<8} {hours_left:<10.1f} {segment:<15} {flags:<15} {traffic_str:<12}")

        print("\n" + "="*90)
        print("\n📊 Легенда:")
        print("  ⚠️  EXPIRING_24H → готов к отправке уведомления (если notified_24h=False)")
        print("  ⚡ EXPIRING_10H → готов к отправке уведомления (если notified_10h=False)")
        print("  TRIAL → пробный ключ (уведомление если used_traffic=0)")
        print("  ACTIVE → ключ активен, уведомления не требуются")
        print("  EXPIRED → ключ истек")

        # Проверяем временное окно
        now = datetime.now()
        in_window = 9 <= now.hour < 23
        window_status = "✅ В окне" if in_window else "❌ ВНЕ окна"
        print(f"\n⏰ Текущее время: {now.strftime('%H:%M:%S')} ({window_status})")
        print(f"   Уведомления отправляются: 9:00 - 22:59")

    finally:
        await conn.close()

asyncio.run(check_status())
EOF
```

---

### Скрипт 4: Очистка тестовых ключей

```bash
cd /home/claude/bot_3xui && python3 << 'EOF'
import asyncio
import asyncpg

DATABASE_URL = "postgresql://claude:7188924Ego@localhost:5432/bot_3xui"

async def cleanup():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("🗑️  Удаление тестовых ключей...\n")

        result = await conn.execute(
            "DELETE FROM keys WHERE email LIKE 'test.%@example.com' AND tg_id = 552810834"
        )

        print(f"✅ Удалено ключей: {result}")
        print("\n✨ Тестовые данные очищены!")

    finally:
        await conn.close()

asyncio.run(cleanup())
EOF
```

---

## 🚀 Быстрый сценарий тестирования

### Шаг 1️⃣ — Создать тестовые ключи
Копируйте **Скрипт 1** в терминал

### Шаг 2️⃣ — Проверить статус
Копируйте **Скрипт 3** в терминал, убедитесь что ключи созданы

### Шаг 3️⃣ — Дождаться цикла уведомлений (или повторить сброс)
- Уведомления отправляются **автоматически каждый час** (в окне 9-23)
- ИЛИ сбросьте флаги (**Скрипт 2**) и повторите проверку (**Скрипт 3**)

### Шаг 4️⃣ — Мониторить логи в отдельном терминале
```bash
tail -f logs/application.log | grep -E "Цикл уведомлений|key_expiry|тг_id"
```

### Шаг 5️⃣ — Проверить результаты в телеграме
Пользователь **552810834** должен получить уведомления для истекающих ключей

### Шаг 6️⃣ — Очистить тестовые данные (опционально)
Копируйте **Скрипт 4** в терминал после завершения тестирования
