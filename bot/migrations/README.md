# Миграции базы данных

## Описание

Папка содержит SQL-скрипты для миграции схемы базы данных в состояние, соответствующее моделям приложения.

## Структура

```
migrations/
├── README.md                      # Этот файл
├── 001_add_missing_tables.sql     # Создание отсутствующих таблиц
├── 002_alter_existing_tables.sql  # Изменение существующих таблиц
├── 003_migrate_gifts.sql          # Миграция таблицы gifts
├── 004_add_indexes_constraints.sql # Индексы и ограничения
└── rollback/
    ├── 004_drop_indexes_constraints.sql
    ├── 003_rollback_gifts.sql
    ├── 002_rollback_alter_tables.sql
    └── 001_drop_tables.sql
```

## Применение миграций

### На тестовом окружении

```bash
# Подключение к тестовой БД
export DATABASE_URL="postgresql://user:pass@localhost:5432/bot_db_test"

# Применить миграции по порядку
psql $DATABASE_URL -f migrations/001_add_missing_tables.sql
psql $DATABASE_URL -f migrations/002_alter_existing_tables.sql
psql $DATABASE_URL -f migrations/003_migrate_gifts.sql
psql $DATABASE_URL -f migrations/004_add_indexes_constraints.sql
```

### На продакшене

```bash
# 1. Сделать бэкап
pg_dump "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Применить миграции
psql "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" -f migrations/001_add_missing_tables.sql
psql "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" -f migrations/002_alter_existing_tables.sql
psql "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" -f migrations/003_migrate_gifts.sql
psql "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" -f migrations/004_add_indexes_constraints.sql

# 3. Проверить результат
psql "postgresql://egorov:tMtB1Ri9JRphMct@localhost:9999/bot_db" -c "\dt"
```

## Откат миграции

```bash
# Откат в обратном порядке
psql $DATABASE_URL -f migrations/rollback/004_drop_indexes_constraints.sql
psql $DATABASE_URL -f migrations/rollback/003_rollback_gifts.sql
psql $DATABASE_URL -f migrations/rollback/002_rollback_alter_tables.sql
psql $DATABASE_URL -f migrations/rollback/001_drop_tables.sql
```

## Чек-лист перед применением

- [ ] Сделан полный бэкап БД (`pg_dump`)
- [ ] Миграция протестирована на staging-окружении
- [ ] Запланировано время простоя (при необходимости)
- [ ] Подготовлен скрипт отката
- [ ] Команда уведомлена о времени миграции

## Описание миграций

### 001_add_missing_tables.sql

Создает отсутствующие таблицы:
- `cache` — для кеширования данных
- `mass_mailing` — для массовых рассылок
- `referral_links` — для реферальных ссылок
- `referral_redemptions` — для активаций реферальных ссылок
- `referral_rewards` — для наград реферальной программы

### 002_alter_existing_tables.sql

Изменяет существующие таблицы:
- `users` — добавляет `balance`, `is_blocked`
- `keys` — добавляет поля тарифа и статистики
- `gift_links` — добавляет поля получателя

### 003_migrate_gifts.sql

Мигрирует таблицу `gifts` к новой структуре:
- Добавляет `token`, `email`, `used_at`
- Переименовывает `selected_months` → `tariff_id` (с миграцией данных)
- Обновляет `gift_redemptions`

### 004_add_indexes_constraints.sql

Создает индексы и ограничения:
- Индексы для новых полей `keys`
- Индексы для реферальных таблиц
- FOREIGN KEY ограничения

## Примечания

1. **Миграция `gifts`** — самая сложная часть. Требуется особая внимательность.
2. **Таблица `referral_*`** — если в БД уже есть данные о рефералах,可能需要 ручная миграция.
3. **Поле `balance`** — если баланс пользователей хранился в кеше, потребуется синхронизация.
