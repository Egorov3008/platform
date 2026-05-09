# Trial Key Dashboard — Design Spec

## Goal

1. Показывать сообщение об отсутствии ключей на дашборде, когда ключей нет.
2. Встроить форму получения пробного ключа прямо в empty state — видна только если `user.trial == 0`.
3. Флоу создания (и продления через существующий UI) соответствует bot-флоу.

---

## UI States

**State 1 — нет ключей + пробный доступен (`trial == 0`):**
- Центрированная карточка с иконкой 🔑, заголовком «У вас нет активных ключей», описанием
- Внутри — блок `trial-block` с бейджем «Бесплатно», параметрами тарифа (30 дней / 1 устройство / безлимит из данных тарифа) и кнопкой «Получить пробный ключ»
- Кнопка вызывает `POST /api/v1/keys/trial` → на успехе перерисовывает дашборд + Toast «Пробный ключ создан»

**State 2 — нет ключей + пробный использован (`trial == 1`):**
- Та же карточка, но без блока `trial-block`. Описание: «Выберите тариф ниже, чтобы подключиться к VPN»

**State 3 — ключи есть:**
- Стандартный grid ключей (существующая логика без изменений)
- Пробный ключ отображается с бейджем «Пробный» (`is_trial == true`)
- Продление через существующую кнопку «Продлить» — backend уже принимает `amount == 0` тарифы

---

## Backend — новый эндпоинт

**`POST /api/v1/keys/trial`** (`backend/api/v1/keys.py`)

Тело запроса: нет (tg_id берётся из query-параметра, как у `/create`)
Query: `tg_id: int`
Auth: `X-Bot-Secret`

Логика (атомарно, зеркалит `CreateFerstKeyScenario` бота):
1. Получить `user` по `tg_id` → 404 если нет
2. Проверить `user.trial == 0` → 403 «Trial already used» если нет
3. Получить тариф `DEFAULT_PRICING_PLAN` → 404 если нет
4. `create_key_svc.proces(tg_id, tariff, server_id=2, conn=pool, number_of_months=1)`
5. `TrialService(service_data).installation_trial(tg_id, pool, trial=1)`
6. Вернуть `KeyResponse` (то же, что `/create`)

Зависимости: `get_pool`, `get_service_data`, `get_cache`, `verify_bot_secret` — уже используются в файле.
Импорт: `TrialService` из `services.core.user.utils.trial`, `DEFAULT_PRICING_PLAN` из `config`.

---

## Web Layer

### `web/app/api/backend_client.py`
Добавить метод `create_trial_key()`:
```python
async def create_trial_key(self) -> dict:
    resp = await self._client.post(
        "/api/v1/keys/trial",
        headers=self._get_headers(),
        params=self._get_params(),
    )
    # raise_for_status логика как у create_key
    return resp.json()
```

### `web/app/api/users.py` (новый файл)
```python
GET /me  →  backend.get_user(tg_id)  →  UserResponse
```
`UserResponse` уже есть в `web/app/schemas/` (или добавить). Возвращает `{tg_id, trial, ...}`.

### `web/app/api/keys.py`
Добавить эндпоинт:
```python
POST /trial  →  backend.create_trial_key()  →  KeyResponse
```
Обёртка с `try/except` по аналогии с `create_key`.

### `web/app/main.py`
Зарегистрировать `users.router` под `prefix="/api/v1/users"`.

---

## Frontend

### `web/frontend/js/pages.js` — `Pages.dashboard()`

Текущий параллельный fetch расширить:
```javascript
const [keys, tariffs, user] = await Promise.all([
    API.get('/keys/').catch(() => []),
    API.get('/tariffs/').catch(() => []),
    API.get('/users/me').catch(() => null),
]);
```

Найти trial-тариф: `const trialTariff = tariffs.find(t => t.amount === 0)`.

При `keys.length === 0`:
- Рендерить `.empty-card` с иконкой и заголовком
- Если `user?.trial === 0`: показать `.trial-block` внутри карточки с данными из `trialTariff` (или fallback «30 дней, 1 устройство, безлимит»)

Обработчик кнопки «Получить пробный ключ»:
```javascript
button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Создаём…';
    try {
        await API.post('/keys/trial', {});
        Toast.success('Пробный ключ создан!');
        Router.render('dashboard');
    } catch (e) {
        Toast.error('Ошибка при создании ключа');
        button.disabled = false;
        button.textContent = 'Получить пробный ключ';
    }
});
```

Для ключей с `is_trial === true` добавить бейдж «Пробный» рядом со статусным.

### `web/frontend/style.css`
Добавить стили: `.empty-card`, `.trial-block`, `.trial-header`, `.trial-badge`, `.trial-features`, `.trial-feat`, `.btn-trial`, `.trial-note`, `.section-count`, `.badge-trial`.

---

## Продление пробного ключа

Не требует изменений. Существующий `POST /keys/{email}/renew` принимает `amount == 0` тарифы.
Кнопка «Продлить» на карточке открывает тарифный выбор — пользователь выбирает тот же тариф для бесплатного продления.
Trial-тариф должен присутствовать в `GET /tariffs/` (проверить `AVAILABLE_RATES` в конфиге).

---

## Верификация

```bash
# 1. Пересобрать backend и web
docker compose build backend web && docker compose up -d

# 2. Открыть http://127.0.0.1:8003/#/dashboard
# 3. Войти как пользователь с trial==0 → увидеть trial-блок
# 4. Нажать «Получить пробный ключ» → должен появиться ключ в списке
# 5. Войти повторно (или обновить) → trial-блок исчез
# 6. На карточке ключа нажать «Продлить» → выбрать тот же тариф → ключ продлён
```

---

## Файлы к изменению

| Файл | Что |
|---|---|
| `backend/api/v1/keys.py` | + `POST /trial` |
| `web/app/api/backend_client.py` | + `create_trial_key()` |
| `web/app/api/users.py` | новый файл, `GET /me` |
| `web/app/api/keys.py` | + `POST /trial` |
| `web/app/main.py` | регистрация users router |
| `web/frontend/js/pages.js` | пустое состояние + trial form |
| `web/frontend/style.css` | стили empty state + trial block |
