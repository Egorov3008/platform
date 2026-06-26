# Web-личный кабинет пользователя — дизайн (одностраничный профиль)

Дата: 2026-06-26
Статус: утверждён (brainstorming)

## Контекст и цель

В монорепо VPN-платформы (`backend` / `bot` / `web`) уже есть частичный кабинет: `web/` — FastAPI-прокси + vanilla-JS SPA (без сборки) с auth через Telegram Widget → JWT в HttpOnly-cookies + CSRF. Текущие пользовательские экраны — `#/dashboard` («Мои ключи» + покупка тарифа) и `#/payments` (история платежей).

Цель — **полная перестройка** пользовательского кабинета в **одностраничный профиль** как единый продукт. Стек прежний (vanilla-JS SPA + FastAPI-прокси), визуальный язык — текущая базовая тема (редизайн структуры/навигации, не внешнего вида). Контракт не меняется: web не лезет в БД, только через `WebBackendClient` с `X-Bot-Secret`.

## Scope (входит)

1. Профиль-шапка: личные данные, баланс, дата регистрации, статус подписки сводкой, trial-флаг, админ-бейдж.
2. Ключи аккордеоном: свёрнуты (email + бейдж статуса + days_left), разворачиваются по клику → детали (expiry_date, grace_expiry, used_traffic, limit_ip, кнопки копировать/продлить/удалить).
3. Empty-state при отсутствии ключей: плашка «Сгенерировать новый ключ» + «Создать пробный ключ» (последняя — только если `trial == 0`).
4. Рефералы — секцией-аккордеоном на той же странице: ссылка, счётчик, награды.
5. Тарифы в ряд снизу: клик по карточке → инлайн-визард (выбор месяцев 1–6 → предпросмотр цены → оплата YooKassa).

## Scope (не входит, YAGNI)

- История платежей (`#/payments`) — убирается.
- Aggregate-эндпоинт `/users/me/cabinet` — параллельный fetch четырёх эндпоинтов на фронтенде достаточен.
- Инструкции/usage-rules/gift-активация — отдельные задачи на будущее.
- Редизайн визуальной темы — остаёмся на текущей базовой.

## Архитектура и навигация

- Стек: vanilla-JS SPA (без сборки) + FastAPI `web/` + backend API. Контракт и auth/CSPF не меняются.
- Роутинг (`web/frontend/js/router.js`): упрощается до `#/login`, `#/profile` (или `#/`), `#/admin`. После логина единственный пользовательский экран — профиль. `#/dashboard` сворачивается в профиль, `#/payments` убирается, `#/admin` остаётся для админов.
- Страница = один модуль рендера `Pages.profile` в `web/frontend/js/pages.js`, который при заходе параллельно тащит `/keys/`, `/tariffs/`, `/users/me`, `/referrals/me/*` и собирает единый DOM. Аккордеоны и визард живут в одном экране, без переходов.
- Навигация: боковой sidebar заменяется компактным topbar (логотип/имя → «Выйти»).
- Auth/CSRF (JWT в HttpOnly + CSRF-токен) — без изменений.

## Лейаут страницы

Сверху вниз, одной колонкой (max-width контейнер, центрирование):

1. **Topbar** — логотип, имя пользователя (username/tg_id), бейдж админа если `is_admin`, кнопка «Выйти».
2. **Профиль-шапка** — карточка: `tg_id`, `username`, `first_name`, `balance` (бейджем), «С нами с: created_at», сводка статуса подписки («Активных ключей: N · Ближайшее истечение: …», считается из ключей), бейдж trial-доступности.
3. **Блок «Ключи» (аккордеон)** — заголовок + счётчик.
   - Empty-state (ключей нет): плашка с кнопками «Сгенерировать новый ключ» (скроллит к тарифам) и, если `trial == 0`, «Создать пробный ключ» (`POST /keys/trial`).
   - Есть ключи: список аккордеон-айтемов. Свёрнутый = `email` · бейдж статуса (active/expiring/expired/grace) · `days_left`. Развёрнутый = `expiry_date`, `grace_expiry` (отдельная строка «grace до …», если есть), `used_traffic` / лимит, `limit_ip`, кнопки «Скопировать ключ», «Продлить» (free → `renew`; paid → скроллит к тарифам), «Удалить».
4. **Блок «Рефералы» (аккордеон)** — реферальная ссылка (копировать), счётчик рефералов, сумма наград.
5. **Блок «Тарифы» (внизу, в ряд)** — grid карточек. Клик → инлайн-визард, поведение зависит от типа тарифа:
   - **Free-тариф (`amount == 0`):** кнопка «Создать ключ» → `POST /keys/create` → перечитать `/keys/`. Без выбора месяцев и оплаты (free-тариф имеет фиксированный период).
   - **Paid-тариф (`amount > 0`):** выбор месяцев 1–6 → предпросмотр цены (`/payments/calculate`) → «Оплатить» (`POST /payments/create`) → редирект на YooKassa `payment_url`.

## Поток данных

На входе в `#/profile` — параллельный fetch через `API`-хелпер:

| Фронтенд → web | web → backend | Назначение |
|---|---|---|
| `GET /api/v1/users/me` | `GET /users/{tg_id}` | профиль-шапка |
| `GET /api/v1/keys/` | `GET /keys/?tg_id=` | список ключей (обогащённый) |
| `GET /api/v1/tariffs/` | `GET /tariffs/` | ряд тарифов |
| `GET /api/v1/referrals/me` | `GET /referrals/{tg_id}` (новый) | реферальная ссылка + статистика |

Действия:
- Создать пробный → `POST /api/v1/keys/trial` → backend `POST /keys/trial`
- Сгенерировать новый (free тариф) → `POST /api/v1/keys/create` → backend `POST /keys/create`
- Продлить free ключ → `POST /api/v1/keys/{email}/renew` → backend `POST /keys/{email}/renew`
- Удалить ключ → `DELETE /api/v1/keys/{email}` → backend `DELETE /keys/{email}`
- Предпросмотр цены → `POST /api/v1/payments/calculate` (новый web-прокси) → backend `POST /payments/calculate`
- Оплатить → `POST /api/v1/payments/create` → backend `POST /payments/create` → редирект на `payment_url`

`WebBackendClient` получает `tg_id` из JWT (через `get_backend_client`), подставляет в query/body. CSRF-токен — на всех мутациях.

## Изменения бэкенда и web-схем

1. **Обогащение `KeyResponse` (backend `app/schemas/keys.py`)** — добавить `status_text`, `days_left`, `hours_left`, `is_active`, `is_trial`, `expiry_date`, `grace_expiry`. Логику вычисления вынести в общий хелпер (переиспользуется и list, и `KeyDetailResponse`), без дублирования.
2. **End-user реферальный эндпоинт (backend)** — новый router `api/v1/referrals.py`, `GET /referrals/{tg_id}` за `verify_bot_secret` → `{referral_link, referrals_count, total_reward}`. Подключить в `api/v1/router.py`.
3. **Web-прокси `/payments/calculate`** — метод `WebBackendClient.calculate_payment` + роут `POST /api/v1/payments/calculate` в `web/app/api/payments.py` (читает `tg_id` из JWT).
4. **Web-прокси `/referrals/me`** — метод `WebBackendClient.get_referral(tg_id)` + роут `GET /api/v1/referrals/me` в новом `web/app/api/referrals.py` (читает `tg_id` из JWT).

Объём: 1 обогащение схемы + 1 новый backend-эндпоинт (referrals) + 2 новых web-прокси.

## Обработка ошибок

- Сетевые/API-ошибки — через существующий `Toast`: 401 → авто-логаут/редирект `#/login`; 403/402 (paid-тариф на free-эндпоинте) → toast «Требуется оплата» + подсветка блока тарифов; 5xx → toast «Ошибка сервера, попробуйте позже».
- Empty-states: нет ключей → плашка генерации; нет рефералов → «Пригласите друга и получите…» со ссылкой; нет тарифов → «Нет доступных тарифов».
- Оптимистичный UI: копирование ключа — локальный успех + toast; удаление/продление/создание — блокировка кнопки на время запроса + перечитать список ключей после успеха (рефрейм данных, не локальная мутация, чтобы статусы/grace были актуальны).
- Конфликты состояния: `trial == 1` + нажата триал-кнопка → backend-ошибка → toast «Пробный уже использован», принудительный переречёт `/users/me`.
- Визард оплаты: пока не пришёл `calculate` — «Оплатить» disabled с лоадером; `create` без `payment_url` → toast «Не удалось создать платёж».

## Тестирование

- **Backend (pytest):** `KeyResponse` содержит статусные/grace-поля — тест на список с активным/истекшим/grace-ключом; `GET /referrals/{tg_id}` — с рефералами и без, проверка `X-Bot-Secret`.
- **Web unit (pytest):** `WebBackendClient.get_referral` / `calculate_payment` — `AsyncMock` httpx (как существующие); web-прокси `/referrals/me` и `/payments/calculate` — `tg_id` из JWT.
- **Web E2E (playwright):** логин → профиль рендерит шапку + аккордеон ключей; раскрытие → детали; empty-state при отсутствии ключей; клик по тарифу → выбор месяцев → предпросмотр цены; реферал-аккордеон показывает ссылку.
- Фронтенд без сборки: E2E по живому SPA, unit по python-части `web/`.

## Ключевые файлы

- SPA shell: `web/app/main.py`, `web/frontend/js/router.js`, `web/frontend/js/pages.js`
- Web API + клиент: `web/app/api/{auth,keys,payments,tariffs,users,admin}.py`, `web/app/api/backend_client.py`, `web/app/core/dependencies.py`
- Web-схемы: `web/app/schemas/{keys,users,payments,tariffs}.py`
- Backend: `backend/api/v1/{keys,payments,tariffs,users,admin,router}.py`, `backend/app/schemas/keys.py`, `backend/models/{users,user}/{keys,key}.py`
- Реферальные модели (для нового эндпоинта): `backend/models/referrals/`