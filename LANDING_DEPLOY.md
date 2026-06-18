# Деплой лендинга «Только для своих» — Telegram без блокировок

**Версия:** MVP, 17.06.2026
**Что в скоупе:** backend API (2 эндпоинта + миграция БД) + статичный лендинг. Бот-часть — следующая итерация.

---

## 0. Что готово

- ✅ `backend/api/v1/landing.py` — `POST /api/v1/landing/quick-key`, `GET /api/v1/landing/state`, `POST /api/v1/landing/mark-converted/{uid}`
- ✅ `backend/models/keys/key.py` — добавлены `converted_tg_id`, `landing_uid` (включая `_DB_FIELDS`)
- ✅ `backend/config.py` — `XUI_INBOUND_ID_LANDING`, `LANDING_COOKIE_SECRET`, `LANDING_PUBLIC_URL`
- ✅ `backend/services/core/keys/utils/{formtion,create_key}.py` — поддержка `inbound_id_override` (обратно совместимо)
- ✅ `bot/migrations/012_add_landing_fields.sql` — миграция БД
- ✅ `web/landing/` — статичный лендинг (index.html, app.js, style.css, robots.txt, sitemap.xml)

---

## 1. Подготовка 3x-UI панели

### 1.1. Создайте новый inbound

Зайдите в панель 3x-UI → **Inbounds** → **Add Inbound**:

| Параметр | Значение |
|---|---|
| Remark | `landing_tg` |
| Protocol | VLESS (или тот же, что основной) |
| Port | новый свободный (например, 8443) |
| Network | TCP или gRPC (для Telegram-доступа) |
| Security | Reality / TLS (по вашему стеку) |
| Enable | true |

**Важно:** На самом inbound НЕ ставьте `limitIp` — это лимит на **подключения к inbound-у**, а нам нужно ограничивать на уровне **отдельного клиента**. Поэтому `limitIp` будет проставляться динамически при создании каждого клиента.

### 1.2. Запишите ID inbound

После создания вы увидите в списке ID (число, обычно >1). Запишите — пригодится для `.env`.

---

## 2. Подготовка Backend

### 2.1. Обновите `.env` (в корне `platform/`)

```bash
# === Landing page (Telegram-доступ без регистрации) ===
# ID inbound, созданного в шаге 1.1
XUI_INBOUND_ID_LANDING=13
# HMAC-секрет для подписи куки. Сгенерируйте:
#   openssl rand -hex 32
LANDING_COOKIE_SECRET=<ваш_секрет_64_hex>
# Публичный URL лендинга
LANDING_PUBLIC_URL=https://telegram.example.com

# === Обязательно добавьте landing inbound в AVAILABLE_CONNECTIONS ===
AVAILABLE_CONNECTIONS=[11, 12, 13]
```

### 2.2. Примените миграцию БД

```bash
cd /home/admin/platform
psql "$DATABASE_URL" -f bot/migrations/012_add_landing_fields.sql
```

Или через docker-compose (если postgres в Docker):

```bash
docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < bot/migrations/012_add_landing_fields.sql
```

Проверка:

```sql
\d keys
-- должны быть: converted_tg_id, landing_uid
```

### 2.3. Перезапустите backend

```bash
docker compose restart backend
# или
cd backend && uvicorn app.main:app --reload
```

Проверка, что эндпоинты поднялись:

```bash
curl http://localhost:8000/api/v1/landing/state -H "X-Bot-Secret: $BOT_SECRET_KEY"
# Должен вернуть {"state":"new"}
```

### 2.4. Проверьте генерацию ключа

```bash
curl -X POST http://localhost:8000/api/v1/landing/quick-key \
  -H "X-Bot-Secret: $BOT_SECRET_KEY" \
  -i
# Должен вернуть 200 + Set-Cookie: tg_landing_id=...; Max-Age=7776000
# + JSON с key_value, deep_link_happ, deep_link_bot
```

---

## 3. Деплой лендинга

### 3.1. Вариант A: под существующим web/ (через nginx + FastAPI)

В `web/frontend/index.html` (или аналогичном шаблоне) добавьте проксирование `/api/v1/landing/*` на backend.

### 3.2. Вариант B: отдельный домен (рекомендую для SEO)

**1. Скопируйте `web/landing/` на сервер:**

```bash
scp -r web/landing/ user@server:/srv/landing/
```

**2. Создайте nginx server block** (`/etc/nginx/sites-available/landing.conf`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name telegram.example.com;

    # Редирект на HTTPS (после настройки сертификата)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name telegram.example.com;

    # SSL (Let's Encrypt)
    ssl_certificate     /etc/letsencrypt/live/telegram.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/telegram.example.com/privkey.pem;

    # Статика лендинга
    root /srv/landing;
    index index.html;

    # Кеширование статики
    location ~* \.(js|css|jpg|png|svg|ico)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # SEO файлы
    location = /robots.txt { }
    location = /sitemap.xml { }

    # API проксируется на backend
    location /api/v1/landing/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # НЕ проксировать Authorization из лендинга — у нас X-Bot-Secret
        # Для лендинга backend сам берёт X-Bot-Secret из env (нужно настроить)
    }

    # Главная страница
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**3. Получите SSL-сертификат:**

```bash
sudo certbot --nginx -d telegram.example.com
```

**4. Активируйте конфиг:**

```bash
sudo ln -s /etc/nginx/sites-available/landing.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.3. **Критично: backend должен принимать запросы с лендинга**

В текущей реализации все эндпоинты в `landing.py` защищены `verify_bot_secret` (заголовок `X-Bot-Secret`). Из браузера этот заголовок **нельзя** установить (CORS блокирует кастомные заголовки).

**Решение:** добавьте CORS-allow для вашего домена лендинга в backend.

В `backend/app/main.py` (или где настраивается CORS) добавьте:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://telegram.example.com",  # ваш домен лендинга
        "http://localhost:8001",           # dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Альтернатива:** откройте `landing.py` и уберите `Depends(verify_bot_secret)` с эндпоинтов `GET /state` и `POST /quick-key` — для лендинга **нет** чувствительных данных, только анонимный ключ. Защита держится на:
- подписанной HMAC-куке (юзер не может сгенерировать чужой landing_uid)
- коротком TTL ключа (24ч)
- `limit_ip=1` (1 устройство)

Бот-эндпоинт `POST /mark-converted/{uid}` **оставьте** под `verify_admin_or_bot` — он вызывается только ботом, а не из браузера.

---

## 4. Smoke-тест в браузере

1. Откройте `https://telegram.example.com/` в режиме инкогнито.
2. Должен быть виден экран **«Telegram без блокировок за 10 секунд»**.
3. Нажмите **«📲 Получить ключ»** → экран **«active»** с обратным отсчётом.
4. Скопируйте ключ → откройте Happ → импортируйте → Telegram должен работать.
5. Перезагрузите страницу → экран **«active»** (кука работает).
6. Подождите ~24ч (или подправьте `expiry_time` в БД вручную) → экран **«expired»**.

---

## 5. Безопасность (чеклист)

- [ ] `LANDING_COOKIE_SECRET` сгенерирован через `openssl rand -hex 32` (не дефолтный)
- [ ] Кука `tg_landing_id` ставится с `httponly=true, samesite=lax, secure=true` (в продакшене через HTTPS)
- [ ] `XUI_INBOUND_ID_LANDING` существует и доступен
- [ ] Inbound для лендинга **отдельный** (не shared с основными клиентами)
- [ ] `limit_ip=1` действительно проставляется (проверьте в 3x-UI: Settings → клиент)
- [ ] CORS на backend разрешает только ваш домен лендинга
- [ ] Nginx скрывает server tokens (`server_tokens off;`)

---

## 6. Что осталось за рамками MVP

- ❌ Хендлер бота `/start landing_<uid>` — следующая итерация
- ❌ Расширение `BackendAPIClient` для бота — следующая итерация
- ❌ A/B-тестирование заголовков лендинга
- ❌ UTM-метки и трекинг конверсий
- ❌ Мониторинг / алерты (например, если 3x-UI недоступен — лендинг не сможет выдать ключ)

---

## 7. Troubleshooting

### «Failed to create landing key»

- Проверьте `XUI_INBOUND_ID_LANDING` в `.env` — должен быть существующий ID
- Проверьте, что inbound добавлен в `AVAILABLE_CONNECTIONS`
- Смотрите логи: `docker compose logs backend | grep landing`

### Кука не ставится

- Включён ли HTTPS? Браузер блокирует cookies с `secure=true` на HTTP
- CORS: проверьте `Access-Control-Allow-Credentials: true` + `Access-Control-Allow-Origin` (НЕ `*`)

### Ключ не работает в Happ

- Проверьте, что inbound для лендинга доступен извне (порт открыт, TLS настроен)
- Скопирован ли vless://... полностью (не обрезан)
- Попробуйте другой клиент (v2rayNG, Streisand) для диагностики

### Ключ истёк слишком быстро

- Проверьте, что бот не удалил клиента из 3x-UI
- Проверьте настройки inbound: `enable=true`, `expiry_time` корректный
