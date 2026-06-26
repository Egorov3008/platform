# Web-личный кабинет пользователя — дизайн (гибрид: 3x-ui страница + web-SPA)

Дата: 2026-06-26
Статус: утверждён (brainstorming)

## Контекст и цель

В монорепо VPN-платформы (`backend` / `bot` / `web`) есть частичный кабинет: `web/` — FastAPI-прокси + vanilla-JS SPA (без сборки) с auth через Telegram Widget → JWT в HttpOnly-cookies + CSRF. Текущие пользовательские экраны — `#/dashboard` («Мои ключи» + покупка тарифа) и `#/payments` (история). Лендинг (`web/landing/`) — отдельная тёмная «Premium Dark» страница (`web/landing/style.css`).

Цель — **полная перестройка** пользовательского кабинета в **гибрид из двух поверхностей**:

1. **3x-ui страница подписки** (кастомный HTML-шаблон, фича v3.3.0, [PR #5079](https://github.com/MHSanaei/3x-ui/pull/5079)) — no-Telegram «ключ-профиль»: статус, трафик, истечение, конфиги, тарифы, кнопка «Продлить». Доступна по URL подписки, который у пользователя уже в конфиге VPN-клиента; **без логина и без Telegram** (знание sub URL = credential). Решает главную боль: при истечении подписки+grace (нет VPN → нет Telegram) пользователь всё равно может открыть страницу и продлить.
2. **web-SPA кабинет** — интерактивный профиль (рефералы, баланс, визард с live-price, обзор всех ключей), вход через кнопку «Профиль» в боте (WebApp initData) + долгоживущая сессия как fallback.

Визуальный язык обеих поверхностей — стиль лендинга «Premium Dark» (переиспользование CSS-переменных/стилей из `web/landing/style.css`): тёмно-синий фон `#020617→#0b1121` со sky-blue радиальными бликами + сетка 64px, акцент `#0ea5e9`, glassmorphism-карточки, Inter + mono для ключей, градиентные кнопки с glow. Логотип — `dlya.svoih` (точка акцентом). Mobile-first, responsive (`@media min-width:640px`). Контракт не меняется: web не лезет в БД, только через `WebBackendClient` с `X-Bot-Secret`.

## Scope (входит)

### Поверхность 1 — 3x-ui страница подписки (no-TG ключ-профиль)
- Кастомный шаблон `sub.html` (Go `html/template`) на файловой системе панели, подключается через Settings → Subscription → Sub Theme Directory (v3.3.0).
- Per-client переменные шаблона: `.links` (конфиги), `.total/.used/.remained` (трафик), `.expire` (истечение, unix sec), `.enabled` (статус), `.subUrl/.subJsonUrl/.subClashUrl`, `.emails`, `.sId`, `.subSupportUrl`.
- Содержимое: статус-бейдж, прогресс-бар трафика, истечение + grace (grace считается из `.expire` + `GRACE_PERIOD_DAYS`), конфиги с копированием, статичные карточки тарифов (1/3/6 мес), кнопка «Продлить» → публичный backend-эндпоинт по `sub_id`.
- Без логина, без Telegram. URL подписки (`Key.key` = `{subscription_url}/{email}`) — уже у пользователя.

### Поверхность 2 — web-SPA кабинет
- Профиль-шапка: личные данные, баланс, дата регистрации, сводка статуса, trial-флаг, админ-бейдж.
- Ключи аккордеоном: свёрнуты (email + бейдж статуса + days_left), разворачиваются → детали (expiry, grace, трафик, limit_ip, копировать/продлить/удалить).
- Empty-state при отсутствии ключей: «Сгенерировать новый ключ» + «Создать пробный ключ» (если `trial == 0`).
- Рефералы — аккордеон: ссылка, счётчик, награды.
- Тарифы в ряд: клик → инлайн-визард (free → `POST /keys/create`; paid → выбор месяцев 1–6 → live-price через `/payments/calculate` → `POST /payments/create` → YooKassa).

### Вход / auth
- **Первичный вход (Telegram доступен):** кнопка «Профиль» в боте — `web_app`-кнопка (`WebAppInfo(url=WEB_URL)`), открывает кабинет в WebView Telegram'а. Telegram инжектит подписанный `initData`; фронт → `POST /auth/exchange {initData}` → web верифицирует тем же `verify_telegram_data` (адаптировать под поля WebApp: `user`, `auth_date`, `hash` + проверка свежести `auth_date`) → upsert `web_users` → JWT-куки → `#/profile`.
- **Долгоживущая сессия (fallback):** refresh-токен ~90 дней в HttpOnly-куке. Кто залогинился через бота, остаётся в сессии; открывает URL кабинета после истечения → продлевает.
- **3x-ui-страница:** без логина (sub URL = credential).

## Scope (не входит, YAGNI)
- История платежей (`#/payments`) — убирается.
- Aggregate-эндпоинт `/users/me/cabinet` — параллельный fetch достаточен.
- Инструкции/usage-rules/gift-активация — отдельные задачи.
- Полный no-Telegram fallback для web-SPA (email magic link / пароль / закладочная ссылка) — не делается: no-Telegram-кейс покрывается 3x-ui-страницей; web-SPA fallback ограничен долгоживущей сессией. Если cookies потеряны + Telegram недоступен — пользователь продляет через 3x-ui-страницу.

## Архитектура и навигация

### web-SPA
- Стек: vanilla-JS SPA (без сборки) + FastAPI `web/` + backend API.
- Роутинг (`web/frontend/js/router.js`): `#/login`, `#/profile` (или `#/`), `#/admin`. После логина единственный пользовательский экран — профиль. `#/dashboard` сворачивается в профиль, `#/payments` убирается, `#/admin` остаётся.
- Страница = один модуль `Pages.profile` в `web/frontend/js/pages.js`, параллельно тащит `/keys/`, `/tariffs/`, `/users/me`, `/referrals/me/*`, собирает единый DOM.
- Навигация: topbar (логотип `dlya.svoih` + бейдж админа + «Выйти»).
- Auth/CSRF (JWT в HttpOnly + CSRF-токен) — без изменений, кроме нового `/auth/exchange`.

### Бот
- Кнопка «Профиль» (`web_app`-тип) в главном меню (`bot/dialogs/windows/widgets/keybord/profile/main.py`) → `WebAppInfo(url=settings.web_url)`.
- `bot/config.py`: добавить `WEB_URL` (базовый URL web-кабинета).

### 3x-ui панель
- Кастомный шаблон подписки (v3.3.0): файл `sub.html` (Go html/template) на панели + Settings → Subscription → Sub Theme Directory. Артефакт живёт на файловой системе панели (deploy-артефакт, не в этом репо — задокументировать установку).

## Лейаут web-SPA

Сверху вниз, одной колонкой (max-width ~720px):
1. **Topbar** — `dlya.svoih`, бейдж админа если `is_admin`, «Выйти».
2. **Профиль-шапка** — `tg_id`, `username`, `first_name`, `balance` (бейдж), «с нами с created_at», сводка «Активных: N · Ближайшее истечение: …», trial-бейдж.
3. **Ключи (аккордеон)** — заголовок + счётчик. Empty-state (нет ключей): «Сгенерировать новый ключ» (скроллит к тарифам) + «Создать пробный ключ» (если `trial == 0`). Есть ключи: свёрнутый = `email` · бейдж статуса · days_left; развёрнутый = expiry, grace, трафик, limit_ip, кнопки копировать/продлить/удалить.
4. **Рефералы (аккордеон)** — ссылка, счётчик, награды.
5. **Тарифы (в ряд)** — grid. Free (`amount==0`) → «Создать ключ» → `POST /keys/create`. Paid → выбор месяцев 1–6 → live-price (`/payments/calculate`) → «Оплатить» (`POST /payments/create`) → YooKassa `payment_url`.

### Responsive / мобильное
Mobile-first через `@media (min-width:640px)`:
- Topbar компактный (логотип + бейдж + короткое имя; «Выйти» → иконка/компактная кнопка).
- Профиль-шапка в столбик; бейджи в строку с wrap; сводка отдельной строкой.
- Аккордеон: тач-цель во всю ширину; детали построчно («метка : значение»); «Скопировать/Продлить» в ряд `flex:1`, «Удалить» на всю ширину.
- Тарифы: стопка на мобильном, 3 колонки на ≥640px.
- Тач-цели ≥40px, шрифт ≥12px, отступы 12–16px. Без сборки — чистый CSS `@media`.

## Лейаут 3x-ui страницы подписки

Центрированная колонка (landing-style, max-width ~680px):
1. Шапка: `dlya.svoih` + «Ваш ключ · {email}» + бейдж статуса (active/expiring/expired/grace, из `.expire` + grace).
2. Трафик: прогресс-бар `.used/.total`, осталось `.remained`, сброс.
3. Параметры: Истекает (из `.expire`), Grace до (`.expire` + GRACE_PERIOD_DAYS), Статус.
4. Конфиги: `{{ range .links }}` с копированием; `.subUrl/.subJsonUrl/.subClashUrl` с копированием.
5. Продлить: статичные карточки тарифов (1/3/6 мес) + кнопка «Продлить» → `https://<backend>/public/renew?sub_id={.sId}&tariff=...&months=...` (публичный эндпоинт, без JWT).
6. Подвал: support (`.subSupportUrl`), заметка «доступно без VPN/TG».

## Поток данных

### 3x-ui страница → backend (без логина)
| Действие | Маршрут | Назначение |
|---|---|---|
| Кнопка «Продлить» | `POST /public/renew {sub_id, tariff_id, months}` (новый, публичный, без JWT) | backend: lookup Key by `sub_id`/`email` → `tg_id` → `POST /payments/create` → вернуть `payment_url` |

Публичный эндпоинт: `sub_id` — secret-credential. В этой платформе `sub_id` панели == `email` клиента (`backend/client.py:507`, `subId` устанавливается равным email при создании), поэтому lookup надёжен по `email` (UNIQUE-индекс): `data_service.keys.get(pool, email=sub_id)` → `key.tg_id` → создать платёж. + rate-limit, + только для существующих ключей, + возвращать только `payment_url`.

### web-SPA → web → backend
| Фронтенд → web | web → backend | Назначение |
|---|---|---|
| `POST /api/v1/auth/exchange` (новый) | — (web верифицирует initData сама) | bot WebApp initData → JWT |
| `GET /api/v1/users/me` | `GET /users/{tg_id}` | профиль-шапка |
| `GET /api/v1/keys/` | `GET /keys/?tg_id=` | список ключей (обогащённый) |
| `GET /api/v1/tariffs/` | `GET /tariffs/` | тарифы |
| `GET /api/v1/referrals/me` | `GET /referrals/{tg_id}` (новый) | рефералы |
| `POST /api/v1/payments/calculate` (новый web-прокси) | `POST /payments/calculate` | live-price в визарде |
| `POST /api/v1/keys/trial` | `POST /keys/trial` | пробный ключ |
| `POST /api/v1/keys/create` | `POST /keys/create` | free-ключ |
| `POST /api/v1/keys/{email}/renew` | `POST /keys/{email}/renew` | продление free |
| `DELETE /api/v1/keys/{email}` | `DELETE /keys/{email}` | удаление |
| `POST /api/v1/payments/create` | `POST /payments/create` | платёж → YooKassa |

## Изменения бэкенда и web-схем

1. **Обогащение `KeyResponse` (backend `app/schemas/keys.py`)** — добавить `status_text`, `days_left`, `hours_left`, `is_active`, `is_trial`, `expiry_date`, `grace_expiry`. Вычисление вынести в общий хелпер (переиспользуется list + `KeyDetailResponse`).
2. **End-user реферальный эндпоинт (backend)** — router `api/v1/referrals.py`, `GET /referrals/{tg_id}` за `verify_bot_secret` → `{referral_link, referrals_count, total_reward}`. Подключить в `api/v1/router.py`.
3. **Публичный payment-эндпоинт по sub_id (backend)** — `POST /public/renew` (без `verify_bot_secret`, без JWT): lookup Key by `sub_id`/`email` → `tg_id` → `POST /payments/create` → `payment_url`. Rate-limit, только существующие ключи. Это позволяет 3x-ui-странице продлевать без логина.
4. **Bot WebApp initData exchange (web)** — `POST /api/v1/auth/exchange {initData}` в `web/app/api/auth.py`; верификация адаптацией `verify_telegram_data` (поля `user`, `auth_date`, `hash` + проверка свежести `auth_date`, например ≤24h); upsert `web_users` → JWT-куки. Переиспользует `login_via_telegram`.
5. **Web-прокси `/payments/calculate`** — `WebBackendClient.calculate_payment` + роут `POST /api/v1/payments/calculate` (читает `tg_id` из JWT).
6. **Web-прокси `/referrals/me`** — `WebBackendClient.get_referral(tg_id)` + роут `GET /api/v1/referrals/me` (читает `tg_id` из JWT).
7. **Bot:** кнопка «Профиль» (`web_app`) в главном меню; `WEB_URL` в `bot/config.py`.
8. **3x-ui шаблон:** файл `sub.html` (landing-style, Go html/template) на панели; документ установки в репо (`docs/`).
9. **Долгоживущая сессия:**延长ить refresh-токен TTL ~90 дней (web `app/core/security.py` / config).

## Обработка ошибок

- **web-SPA:** через существующий `Toast`: 401 → авто-логаут/`#/login`; 403/402 → «Требуется оплата» + подсветка тарифов; 5xx → «Ошибка сервера». Empty-states: нет ключей → плашка; нет рефералов → «Пригласите друга…»; нет тарифов → «Нет тарифов». Оптимистичный UI: копирование — локальный toast; мутации — блокировка кнопки + перечитать `/keys/`. Конфликт `trial==1` → toast «Пробный уже использован», перечитать `/users/me`. Визард: «Оплатить» disabled пока нет `calculate`; `create` без `payment_url` → toast.
- **`/auth/exchange`:** невалидный `initData` (подпись/`auth_date` просрочен) → 401, фронт → `#/login` (предложить обычный Telegram Widget).
- **`/public/renew`:** невалидный/чужой `sub_id` → 404; rate-limit превышен → 429; backend-ошибка создания платежа → 502 с сообщением.

## Тестирование

- **Backend (pytest):** `KeyResponse` с grace/status-полями (активный/истекший/grace); `GET /referrals/{tg_id}` (с/без рефералов, `X-Bot-Secret`); `POST /public/renew` — валидный `sub_id` → `payment_url`, чужой/несуществующий → 404, rate-limit.
- **Web unit (pytest):** `WebBackendClient.get_referral`/`calculate_payment` (`AsyncMock`); web-прокси `/referrals/me`, `/payments/calculate` (`tg_id` из JWT); `verify_telegram_data` адаптация для WebApp initData (валидный/невалидный/просроченный `auth_date`).
- **Web E2E (playwright):** логин → профиль (шапка + аккордеон ключей); раскрытие → детали; empty-state; клик тарифа → выбор месяцев → live-price; реферал-аккордеон; responsive (мобильный вид).
- **3x-ui шаблон:** ручная проверка — открыть sub URL в браузере (не VPN-клиентом) → рендерится HTML профиль; «Продлить» → `payment_url`.
- Фронтенд без сборки: E2E по живому SPA, unit по python-части `web/`.

## Ключевые файлы

- SPA shell: `web/app/main.py`, `web/frontend/js/{router,pages,auth,api}.js`
- Web API + клиент: `web/app/api/{auth,keys,payments,tariffs,users}.py`, `web/app/api/backend_client.py`, `web/app/core/{security,dependencies,csrf}.py`
- Web-схемы: `web/app/schemas/{keys,users,payments,tariffs,auth}.py`
- Backend: `backend/api/v1/{keys,payments,tariffs,users,router}.py`, `backend/app/schemas/keys.py`, `backend/app/services_auth.py`
- Backend 3x-ui клиент: `backend/client.py`, `backend/services/core/keys/utils/{grace,status,formtion}.py`
- Bot: `bot/dialogs/windows/widgets/keybord/profile/main.py`, `bot/config.py`
- Лендинг (визуальный референс): `web/landing/style.css`, `web/landing/index.html`
- 3x-ui шаблон (новый артефакт): `sub.html` на панели + `docs/` установка
- Реферальные модели: `backend/models/referrals/`

## Риски и зависимости

- **3x-ui v3.3.0 breaking change:** `/panel/setting` и `/panel/xray` переехали под `/panel/api`. Проверить, не заденет ли используемые бэкендом `/panel/login`, `/panel/csrf-token`, `/api/clients/*` (вероятно нет, но проверить при работе).
- **3x-ui шаблон — артефакт на панели**, не в репо: задокументировать установку; обновления шаблона требуют деплоя на файловую систему панели.
- **`/public/renew` — публичный эндпоинт создания платежа:** `sub_id` — единственный секрет; обязателен rate-limit и проверка существования ключа. Не возвращать лишних данных (только `payment_url`).
- **Key retention после expiry:** UUID→tg_id login-lookup и `/public/renew` по sub_id работают, потому что `expire_after_grace` (удаление panel-клиента) — dead code, и DB-рядок Key сохраняется. **Зависимость:** если кто-то подключит `expire_after_grace`, panel_sync `_cleanup_orphaned_keys` удалит DB-рядок и fallback сломается. Зафиксировать тестом/документом.
- **Нет индекса на `client_id`:** lookup по `client_id` — seq scan. Добавить `CREATE INDEX idx_keys_client_id ON keys(client_id)` (для путей, использующих UUID-lookup; для `/public/renew` lookup по `email`/`sub_id` — проверить индекс).
- **Landing 24h-ключи** имеют псевдо `tg_id` (`< 0`) до конверсии: исключать из lookup-логики (`tg_id > 0` и не unconverted landing).