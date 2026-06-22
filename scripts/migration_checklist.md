# Миграция VPN Platform на новый сервер

> Скрипты расположены в `scripts/`.  
> Доступны два сценария:
> 1. **Полный архив** — весь проект + данные (`migration_export.sh` → `migration_import.sh`).
> 2. **Только данные** — код забирается из GitHub, в архиве лежат `.env`, БД, сертификаты (`migration_export_data_only.sh` → `migration_import_from_git.sh`).
>
> Перед запуском в production обязательно прочитай этот чеклист.

## Что переносится

- `postgres_data` через `pg_dump` / `pg_restore` (все таблицы + данные)
- `.env` с секретами
- SSL-сертификаты `nginx_certs/`
- Логи и видео-инструкции бота (`bot/logs`, `bot/logs_error`, `bot/video_instructions`)
- При полном архиве также копируется весь исходный код

## Что нужно подготовить ДО миграции

1. **Доступы:**
   - root / sudo на старом и новом сервере.
   - SSH-ключ или пароль для передачи архива между серверами.
   - Токен бота, реквизиты YooKassa, доступ к 3x-UI панели.

2. **На новом сервере:**
   - Установлен Docker + Docker Compose plugin (`docker compose`).
   - Установлен `git` и `python3`.
   - Указанный вами домен уже ведёт на IP нового сервера.
   - Открыты порты 80, 443, 5433 (если хотите подключаться к БД с хоста).

3. **Решите про SSL:**
   - Вариант A: перенести старые сертификаты (`nginx_certs/fullchain.pem`, `privkey.pem`) — быстро, но им нужен тот же домен.
   - Вариант B: получить новые через Certbot — предпочтительно при смене домена.

---

# Сценарий 1: код из GitHub (рекомендуется)

## 1. Экспорт на старом сервере

```bash
cd /home/admin/platform
bash scripts/migration_export_data_only.sh /home/admin/platform /tmp/vpn-migration-data
```

Результат: `/tmp/vpn-migration-data/vpn-migration-data-YYYYMMDD-HHMMSS.tar.gz`.

## 2. Перенос файлов на новый сервер

```bash
# На старом сервере:
scp /tmp/vpn-migration-data/vpn-migration-data-*.tar.gz root@NEW_SERVER:/opt/
```

## 3. Импорт на новом сервере

```bash
# Замените URL репозитория, ветку, путь к архиву и домен
bash /opt/vpn-migration-data-YYYYMMDD-HHMMSS/scripts/migration_import_from_git.sh \
  "https://github.com/OWNER/REPO.git" \
  "main" \
  "/opt/vpn-migration-data-YYYYMMDD-HHMMSS.tar.gz" \
  "your-new-domain.com" \
  "/home/admin/platform"
```

Скрипт:
- клонирует/обновляет репозиторий в `/home/admin/platform`
- копирует `.env`, сертификаты, логи и видео из архива
- обновит `WEBHOOK_BASE_URL` и `URL_BOT` под новый домен
- обновит `server_name` в `nginx/nginx.conf`
- при необходимости запустит Certbot
- восстановит БД из дампа
- соберёт и запустит `docker compose up --build -d`
- проверит health backend и web

---

# Сценарий 2: полный архив (если GitHub нет или нужен полный слепок)

## 1. Экспорт на старом сервере

```bash
cd /home/admin/platform
bash scripts/migration_export.sh /home/admin/platform /tmp/vpn-migration
```

Результат: `/tmp/vpn-migration/vpn-platform-YYYYMMDD-HHMMSS.tar.gz`.

## 2. Перенос файлов на новый сервер

```bash
# На старом сервере:
scp /tmp/vpn-migration/vpn-platform-*.tar.gz root@NEW_SERVER:/opt/
```

## 3. Импорт на новом сервере

```bash
cd /opt
bash /opt/vpn-migration/vpn-platform-YYYYMMDD-HHMMSS/scripts/migration_import.sh \
  /opt/vpn-migration/vpn-platform-YYYYMMDD-HHMMSS.tar.gz \
  your-new-domain.com \
  /home/admin/platform
```

---

## Обязательные ручные действия после миграции

### YooKassa webhook

В личном кабинете YooKassa смените URL вебхука на новый:

```
https://your-new-domain.com/api/v1/payments/webhook
```

Или через API:

```bash
# Замените SHOP_ID и SECRET_KEY
YOOKASSA_SHOP_ID=... YOOKASSA_SECRET_KEY=... \
curl -X POST https://api.yookassa.ru/v3/webhooks \
  -u "$YOOKASSA_SHOP_ID:$YOOKASSA_SECRET_KEY" \
  -H "Idempotence-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "payment.succeeded",
    "url": "https://your-new-domain.com/api/v1/payments/webhook"
  }'
```

### Telegram Bot

- Если в `.env` поменялся `TELEGRAM_BOT_USERNAME` или `URL_BOT` — обновите ссылки в боте и на сайте.
- Если бот работает через webhook (в текущем compose бот использует polling), обновите webhook URL через @BotFather или API.

### 3x-UI Panel

- Если IP/домен панели изменился — обновите `XUI_API_URL` и `XUI_SUB` в `.env`.
- Убедитесь, что новый сервер имеет доступ к панели по указанным URL.

### DNS

Убедитесь, что A-запись домена указывает на новый сервер. SSL-сертификат не выдастся, пока DNS не обновится.

## Проверка

```bash
cd /home/admin/platform
docker compose ps
docker compose logs -f
```

Проверьте:
- `https://your-new-domain.com/` открывается.
- `https://your-new-domain.com/api/v1/payments/webhook` отвечает `{"ok":true}` на GET.
- Бот отвечает в Telegram.
- В логах backend нет ошибок подключения к 3x-UI и БД.

## Откат (если что-то пошло не так)

На старом сервере:

```bash
cd /home/admin/platform
docker compose up -d
```

Архив с бэкапом можно переиспользовать, если нужно повторить миграцию.

## Важные замечания по безопасности

- **Никогда не выкладывайте архив миграции в публичный доступ.** В нём лежит `.env` с токенами и ключами, а также полный дамп БД.
- После переноса смените `BOT_SECRET_KEY`, `ADMIN_API_KEY`, `SECRET_KEY` и ключи YooKassa, если старые сервер могли быть скомпрометированы.
- Удалите временные бэкапы с обоих серверов после успешной миграции:
  ```bash
  rm -rf /tmp/vpn-migration /tmp/vpn-migration-data /opt/vpn-migration /opt/vpn-migration-data
  ```

## Структура архива "только данные"

```
vpn-migration-data-YYYYMMDD-HHMMSS/
├── .env                     # секреты
├── nginx_certs/             # SSL
├── bot/
│   ├── logs/
│   ├── logs_error/
│   └── video_instructions/
├── db_backup/
│   ├── bot_db.custom.dump   # pg_dump -Fc
│   └── bot_db.plain.sql     # pg_dump -Fp
└── meta/
    ├── source_host.txt
    └── export_timestamp.txt
```

## Структура полного архива

```
vpn-platform-YYYYMMDD-HHMMSS/
├── project/                 # полная копия /home/admin/platform
│   ├── .env
│   ├── backend/
│   ├── bot/
│   ├── web/
│   ├── nginx/
│   ├── nginx_certs/
│   ├── shared/
│   ├── docker-compose.yml
│   └── ...
├── db_backup/
│   ├── bot_db.custom.dump
│   └── bot_db.plain.sql
└── meta/
    ├── source_host.txt
    ├── export_timestamp.txt
    └── docker_images.txt
```
