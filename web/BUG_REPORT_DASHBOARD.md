# Bug Report: Dashboard не загружается после авторизации

## Дата: 11 апреля 2026

---

## 🐛 Описание проблемы

Пользователь авторизуется (email/password), переходит на `http://localhost:8001/#/dashboard`, но страница не загружается.

---

## 🔍 Найденные баги

### BUG #1: Неправильный порт (КРИТИЧНЫЙ)

**Проблема:** Пользователь пытается зайти на порт **8001**, но приложение слушает порт **8000**.

**Где:** `docker-compose.yml`
```yaml
ports:
  - "8000:8000"  # Не 8001!
```

**Решение:** Использовать `http://localhost:8000/#/dashboard`

---

### BUG #2: Создание ключа невозможно без Telegram (ВЫСОКИЙ)

**Проблема:** 
1. Пользователь регистрируется по email → `tg_id = null` в JWT токене
2. Dashboard загружается, показывает "У вас пока нет ключей"
3. Пользователь нажимает "Создать ключ" → выбирает тариф → отправляет запрос
4. Бэкенд возвращает **403 Forbidden**: `"Telegram account required to manage keys"`
5. Фронтенд **молча проглатывает** ошибку через `.catch(() => [])`
6. Ничего не происходит, пользователь в замешательстве

**Затронутые файлы:**
- `frontend/index.html` (строка ~1112, обработка ошибок `.catch(() => [])`)
- `app/api/keys.py` (строка 28-33, `_require_tg_id`)

**Код фронтенда:**
```javascript
const [keys, tariffs] = await Promise.all([
    API.get('/keys/').catch(() => []),  // ← ТИХО пропускает 403!
    API.get('/tariffs/').catch(() => []),
]);
```

**Код бэкенда:**
```python
def _require_tg_id(current_user: dict) -> int:
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram account required to manage keys",
        )
    return tg_id
```

**Решение:**
1. Добавить проверку на фронтенде: если у пользователя `tg_id = null`, показать сообщение "Для создания ключей необходимо привязать Telegram аккаунт"
2. Или добавить кнопку "Привязать Telegram" в дашборд
3. Или разрешить создание ключей без Telegram (изменить бэкенд)

---

### BUG #3: Ошибки API не отображаются пользователю (СРЕДНИЙ)

**Проблема:** Все ошибки API в dashboard заглушаются через `.catch(() => [])`

**Затронутые строки:** `frontend/index.html` строки ~1112-1115

```javascript
const [keys, tariffs] = await Promise.all([
    API.get('/keys/').catch(() => []),      // 403 → []
    API.get('/tariffs/').catch(() => []),   // 500 → []
]);
```

**Последствия:**
- Ошибка 403 (нет Telegram) → пустой список
- Ошибка 500 (сервер упал) → пустой список  
- Ошибка 503 (БД недоступна) → пустой список

Пользователь видит "У вас пока нет ключей" вместо реальной ошибки.

**Решение:** 
```javascript
const [keys, tariffs] = await Promise.all([
    API.get('/keys/').catch(err => {
        console.error('Keys API error:', err);
        Toast.error('Не удалось загрузить ключи');
        return [];
    }),
    API.get('/tariffs/').catch(err => {
        console.error('Tariffs API error:', err);
        Toast.error('Не удалось загрузить тарифы');
        return [];
    }),
]);
```

---

### BUG #4: 401 обработка может оставить пользователя на dashboard (НИЗКИЙ)

**Проблема:** Если access token истёк и refresh не удался:
1. `API.get('/keys/')` → 401
2. `Auth.refresh()` → fail → `Auth.logout()` → редирект на `#/login`
3. **НО:** Promise reject пробрасывается выше
4. Dashboard catch block ловит ошибку и показывает "Ошибка загрузки"
5. Пользователь видит ошибку на dashboard хотя уже разлогинен

**Код:**
```javascript
// API.request() при 401:
Auth.logout();  // ← Редирект на #/login
throw new Error('Необходима авторизация');  // ← Но promise reject остаётся

// dashboard():
} catch (err) {
    // err = "Необходима авторизация"
    // Показываем "Ошибка загрузки" на dashboard
    container.innerHTML = `<div class="empty-state">...</div>`;
}
```

**Решение:** Проверять `Auth.isLoggedIn()` в catch block перед рендером ошибки

---

## 📊 Приоритеты исправления

| # | Баг | Приоритет | Сложность | Статус |
|---|-----|-----------|-----------|--------|
| 1 | Неправильный порт | **Критичный** | 0 мин (документация) | ✅ Исправлено (документация) |
| 2 | Нельзя создать ключ без Telegram | **Высокий** | 30 мин | ✅ Исправлено |
| 3 | Ошибки API не показываются | **Средний** | 15 мин | ✅ Исправлено |
| 4 | 401 обработка | **Низкий** | 20 мин | ✅ Исправлено |

---

## ✅ Выполненные исправления

### BUG #2 — Проверка Telegram аккаунта (frontend/index.html)

**Что изменено:**
1. Добавлена проверка `tg_id` в payload токена при загрузке dashboard
2. Если `tg_id = null`, показывается сообщение "Необходимо привязать Telegram" вместо "У вас пока нет ключей"
3. Кнопка "+ Создать ключ" **не отображается** если у пользователя нет Telegram
4. Пользователь без Telegram видит понятное объяснение почему не может создать ключи

**Код:**
```javascript
// Проверка наличия Telegram аккаунта у пользователя
const token = Auth.getAccessToken();
const userPayload = token ? Auth.decodeToken(token) : null;
const hasTelegram = userPayload && userPayload.tg_id;

// ...
${hasTelegram ? '<button class="btn btn-primary btn-sm" id="createKeyBtn">+ Создать ключ</button>' : ''}
```

### BUG #3 — Обработка ошибок API (frontend/index.html)

**Что изменено:**
1. Заменены заглушки `.catch(() => [])` на `.catch(err => { Toast.error('...'); return []; })`
2. Теперь пользователь видит Toast с ошибкой если API недоступен
3. Ошибки логируются в консоль для отладки

**Код:**
```javascript
const [keys, tariffs] = await Promise.all([
    API.get('/keys/').catch(err => {
        console.error('Ошибка загрузки ключей:', err);
        Toast.error('Не удалось загрузить ключи');
        return [];
    }),
    API.get('/tariffs/').catch(err => {
        console.error('Ошибка загрузки тарифов:', err);
        Toast.error('Не удалось загрузить тарифы');
        return [];
    }),
]);
```

### BUG #4 — Обработка 401 (frontend/index.html)

**Что изменено:**
1. В catch block dashboard добавлена проверка `Auth.isLoggedIn()`
2. Если пользователь разлогинен (после 401), ошибка не показывается
3. Router сам редиректит на `#/login`, dashboard не рендерит "Ошибка загрузки"

**Код:**
```javascript
} catch (err) {
    // Если пользователь разлогинен (например после 401), не показываем ошибку — router уже редиректит
    if (!Auth.isLoggedIn()) {
        return;
    }
    container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3>...</div>`;
}
```

### Тестирование исправлений

- ✅ JavaScript синтаксис проверен (Node.js `new Function()`)
- ✅ Фронтенд отдаётся сервером с изменениями (проверено через `curl`)
- ✅ API эндпоинты работают как ожидается
- ✅ Пользователи без Telegram получают пустой список ключей (200 OK)
- ✅ Попытка создать ключ без Telegram возвращает 403 (ожидаемо)

---

## 🔧 Рекомендации по исправлению

### Для BUG #2 (Telegram required):

**Вариант A: Добавить проверку на фронтенде**

В `Pages.dashboard()` после загрузки данных:

```javascript
// Проверить есть ли tg_id у пользователя
const token = Auth.getAccessToken();
const payload = Auth.decodeToken(token);
const hasTelegram = payload && payload.tg_id;

if (!hasTelegram) {
    container.innerHTML = `
        <div class="empty-state">
            <svg><!-- Telegram icon --></svg>
            <h3>Необходимо привязать Telegram</h3>
            <p>Для создания VPN ключей нужно привязать Telegram аккаунт</p>
            <button class="btn btn-primary mt-16" onclick="/* open Telegram link */">
                Привязать Telegram
            </button>
        </div>
    `;
    // Скрыть кнопку "Создать ключ"
    return;
}
```

**Вариант B: Изменить бэкенд**

Разрешить создание ключей без Telegram, используя `sub` (user id из web_users) вместо `tg_id`.

---

### Для BUG #3 (Error handling):

Заменить все `.catch(() => [])` на `.catch(err => { Toast.error('...'); return []; })`

---

### Для BUG #4 (401 handling):

В `dashboard()` catch block:

```javascript
} catch (err) {
    // Если пользователь разлогинен, не показывать ошибку
    if (!Auth.isLoggedIn()) {
        return; // Router уже редиректит на login
    }
    container.innerHTML = `<div class="empty-state">...</div>`;
}
```

---

## ✅ Чеклист для проверки

- [ ] Пользователь может зайти на `http://localhost:8000/#/dashboard` (не 8001!)
- [ ] После авторизации токен сохраняется в localStorage
- [ ] Dashboard загружается и показывает ключи (или empty state)
- [ ] Пользователь без Telegram видит понятное сообщение
- [ ] Ошибки API отображаются через Toast
- [ ] При истёкшем токене происходит редирект на login без ошибок
