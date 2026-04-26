# Полный сценарий регистрации пользователя

Документ описывает полный поток регистрации нового пользователя в боте: от команды `/start` через диалоги регистрации до создания первого VPN-ключа.

## Содержание

1. [Обзор](#обзор)
2. [Три типа регистрации](#три-типа-регистрации)
3. [Фаза 1: Проверка пользователя](#фаза-1-проверка-пользователя)
4. [Фаза 2: Обработка токена регистрации](#фаза-2-обработка-токена-регистрации)
5. [Фаза 3: Диалоговый флоу](#фаза-3-диалоговый-флоу)
6. [Фаза 4: Создание первого ключа](#фаза-4-создание-первого-ключа)
7. [Полная диаграмма](#полная-диаграмма)
8. [Примеры](#примеры)

---

## Обзор

Регистрация состоит из **4 фаз** и может быть **трёх типов**:

```
Пользователь: /start [token]
           ↓
       Фаза 1: RegistrationUsersMiddleware проверяет кеш
           ↓
       Фаза 2: RegistrationFactory определяет тип (gift/referral/unknown)
           ↓
       Фаза 3: DialogManager открывает диалоговое окно
           ↓
       Фаза 4: CreateFerstKeyScenario создаёт первый ключ
           ↓
       Результат: User + Key в БД, пользователь в MainMenu
```

**Время прохождения регистрации:**
- Без токена (обычная): ~3-5 сек (диалоговый флоу)
- С подарочной ссылкой: ~2-3 сек (автоматическая активация)
- С реферальной ссылкой: ~2-3 сек (автоматическая активация)

---

## Три типа регистрации

### 1️⃣ **Обычная регистрация** (без токена)

**Сценарий:** Пользователь, пришедший без специальной ссылки

```
Команда:  /start
Тип:      "unknown_user"
Флоу:     Диалоговая форма заявки на регистрацию
Результат: Ручное одобрение администратором (если реализовано)
```

**Файлы:**
- `dialogs/windows/widgets/message/register/welcome.py` — приветствие
- `dialogs/windows/widgets/message/register/sending.py` — форма заявки
- `states/registrate.py` — FSM-состояния (welcome, sending_registration, sender)

### 2️⃣ **Подарочная регистрация** (gift token)

**Сценарий:** Пользователь переходит по подарочной ссылке

```
Команда:  /start gift_abc123xyz
Тип:      "gift"
Флоу:     Автоматическая активация подарка
Результат: Пользователь сразу получает ключ, указанный в подарке
```

**Файлы:**
- `registration/gift_registration.py` — проверка подарочной ссылки
- `services/scenarios/gift_scenario.py` — активация подарка

**Данные подарка:**
```python
{
    "type": "gift",
    "token": "gift_abc123xyz",
    "tariff_id": 10,           # какой тариф дарим
    "from_user_id": 123456,    # кто отправил подарок
}
```

### 3️⃣ **Реферальная регистрация** (referral token)

**Сценарий:** Пользователь переходит по реферальной ссылке

```
Команда:  /start ref_user_123456
Тип:      "referral"
Флоу:     Автоматическая активация или диалоговый выбор тарифа
Результат: Новый пользователь + реферер получает бонус
```

**Примечание:** Реферальная регистрация декларируется в документации, но реализация может варьироваться.

---

## Фаза 1: Проверка пользователя

**Компонент:** `middlewares/registration_users.py:RegistrationUsersMiddleware`

### Порядок действий

```python
async def __call__(self, handler, event, data):
    container = data["container"]
    cache = data["cache"]
    user_id = event.from_user.id

    # Шаг 1: Проверить кеш
    cached_user = await cache.users.get(CacheKeyManager.user(user_id))
    if cached_user:
        # ✅ Пользователь известен → registered_user
        data["registration_result"] = {
            "success": True,
            "type": "registered_user"
        }
        return await handler(event, data)

    # Шаг 2: Fallback — проверить БД (если кеш истек)
    try:
        service_model = container.resolve(ServiceDataModel)
        db_user = await service_model.users.get_data(user_id)
        if db_user:
            # ✅ Найден в БД → registered_user
            data["registration_result"] = {
                "success": True,
                "type": "registered_user"
            }
            return await handler(event, data)
    except Exception as e:
        logger.warning("DB fallback error", user_id=user_id)

    # Шаг 3: Новый пользователь — извлечь токен из /start
    token = await self.get_start_message(event)  # /start abc123 → "abc123"
    if not token:
        # Нет токена → unknown_user
        return await handler(event, data)

    # Шаг 4: Проверить токен (gift, referral, или неизвестный)
    factory = container.resolve(RegistrationFactory)
    gift_registration = container.resolve(GiftRegistration)

    factory.register_handler(gift_registration)
    result = await factory.handle_registration(token)

    if result["success"]:
        data["registration_result"] = result

    return await handler(event, data)
```

### Результаты проверки

| Сценарий | `registration_result` |
|----------|----------------------|
| Пользователь в кеше | `{success: True, type: "registered_user"}` |
| Пользователь в БД | `{success: True, type: "registered_user"}` |
| Новый с gift токеном | `{success: True, type: "gift", tariff_id: 10, ...}` |
| Новый с ref токеном | `{success: True, type: "referral", ...}` |
| Новый без токена | `{success: True, type: "unknown_user"}` |

---

## Фаза 2: Обработка токена регистрации

**Компонент:** `registration/registration_factory.py`

### Архитектура

```
RegistrationFactory (фабрика)
    ├── GiftRegistration (обработчик подарков)
    └── ReferralRegistration (обработчик рефералов, если реализована)
    └── Unknown → {type: "unknown_user"}
```

### Процесс поиска обработчика

```python
async def handle_registration(self, token: str) -> Dict[str, Any]:
    """Находит первый обработчик, который может обработать токен"""
    for handler in self._handlers:
        if await handler.can_handle(token):
            return await handler.register(token)
    # Если ни один обработчик не подошёл
    return {"success": True, "type": "unknown_user"}
```

### GiftRegistration детально

**Файл:** `registration/gift_registration.py`

```python
class GiftRegistration(BaseRegistration):
    def __init__(self, service: ServiceDataModel):
        self._gift_data = service.gifts

    async def can_handle(self, token: str) -> bool:
        """Проверяет:
        1. Ссылка существует в БД
        2. Ссылка ещё не использована (is_redeemable)
        """
        gift_link = await self._gift_data.get_by(token=token)
        if not gift_link:
            return False
        return gift_link.is_redeemable()

    async def register(self, token: str) -> Dict[str, Any]:
        """Возвращает данные подарка"""
        gift_link = await self._gift_data.get_by(token=token)
        return {
            "success": True,
            "type": "gift",
            "token": token,
            "tariff_id": gift_link.tariff_id,
            "from_user_id": gift_link.sender_tg_id,
        }
```

**Что проверяет `is_redeemable()`:**
- Ссылка не использована (not used)
- Ссылка не истекла (deadline > now)
- Тариф существует и активен

---

## Фаза 3: Диалоговый флоу

**Компонент:** `handlers/start.py`

После получения `registration_result` от middleware бот перенаправляет в зависимости от типа.

### Маршрутизация

```python
@router.message(Command("start"))
async def send_massage_registration(
    message: Message, dialog_manager: DialogManager
) -> None:
    result_registration = dialog_manager.middleware_data.get("registration_result")
    type_registration = result_registration.get("type")

    if type_registration == "unknown_user":
        # 👤 Обычная регистрация → диалоговая форма
        await dialog_manager.start(Register.welcome, mode=StartMode.RESET_STACK)

    elif type_registration == "gift":
        # 🎁 Подарочная регистрация → автоматическая активация
        container = dialog_manager.middleware_data.get("container")
        service_model = container.resolve(ServiceDataModel)
        saver = container.resolve(SeverUser)
        cache = dialog_manager.middleware_data.get("cache")

        gift_scenario = GiftActivationScenario(
            dialog_manager=dialog_manager,
            service_model=service_model,
            saver=saver,
            cache=cache,
        )
        await gift_scenario.start()

    elif type_registration == "registered_user":
        # ✅ Уже зарегистрирован → главное меню
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)

    else:
        raise AttributeError("Unknown registration type")
```

### Диалоговое окно: Register.welcome

**Файлы:**
- `states/registrate.py` — FSM-состояния
- `dialogs/windows/widgets/message/register/welcome.py` — сообщение
- `dialogs/windows/widgets/keybord/register/...` — кнопки (если есть)

```python
class RegisterWelcomeMessage(MessageBuilder):
    def build(self) -> Text:
        return Const("""
        👋 Добро пожаловать в VPN-бот!

        Это сервис для управления VPN-подписками.
        Нажми кнопку ниже, чтобы продолжить регистрацию.
        """)
```

**Кнопки:**
- `[Начать регистрацию]` → переход на Register.sending_registration

### Диалоговое окно: Register.sending_registration

```python
class RegisterSendingMessage(MessageBuilder):
    def build(self) -> Text:
        return Format("""
        📝 ✅ Форма заполнена.
        Вас пригласил {username}!

        Теперь вы можете подать заявку на регистрацию.
        """)
```

**Кнопки:**
- `[Отправить заявку]` → Register.sender

### Диалоговое окно: Register.sender

```
Окончание регистрации:
✅ Заявка отправлена!

Ожидайте подтверждения администратора.
Вам будет отправлено уведомление.
```

---

## Фаза 4: Создание первого ключа

**Компонент:** `services/scenarios/create_first_key_scenario.py:CreateFerstKeyScenario`

После завершения диалога регистрации (или сразу для gift-регистрации) запускается сценарий создания первого ключа.

### Архитектура сценария

```python
class CreateFerstKeyScenario(ScenarioFactory):
    def __init__(
        self,
        cache: CacheService,
        model_data: ServiceDataModel,
        create_key: CreateKey,
        gift_service: GiftLinkProvider,
        trial_user: TrialService,
        conn: asyncpg.Pool,
        dialog_manager: DialogManager,
    ):
        # Инжекция зависимостей
        self.cache = cache
        self.tariff_data = model_data.tariffs
        self.user_data = model_data.users
        self.create_key = create_key
        ...
```

### Шаги создания ключа

#### 1. Получить данные регистрации

```python
async def get_data(self):
    # Получить пользователя из диалога
    tg_id = self.dialog_manager.event.from_user.id

    # Получить тариф (из DEFAULT_PRICING_PLAN в env или из gift)
    tariff_id = int(DEFAULT_PRICING_PLAN)  # "10" → 10
    self._tariff = await self.tariff_data.get_data(tariff_id)

    if not self._tariff:
        raise ValueError(f"Tariff {tariff_id} not found")
```

#### 2. Создать User в БД

```python
async def create_user(self, tg_id: int):
    # Сохранить пользователя в БД
    user = User(
        tg_id=tg_id,
        username=None,
        email=None,
        trial=0,  # нет пробного периода
        referred_by=None,
    )

    # Сохранить в БД + кеш
    await self.user_data.insert(user)
    await self.cache.users.set(
        CacheKeyManager.user(tg_id),
        user
    )
    return user
```

#### 3. Создать VPN-ключ на 3x-ui панели

```python
async def start(self):
    # Вызвать CreateKey для создания ключа на панели
    key = await self.create_key.run(
        tariff_id=self._tariff.id,
        user_id=self._user.tg_id,
    )

    # CreateKey возвращает объект Key с:
    # - email (идентификатор ключа)
    # - password
    # - protocol
    # - expiry_date
    # - traffic_limit
    # - server_id
```

#### 4. Сохранить Key в БД и кеш

```python
# Сохранить в БД
await self.key_data.insert(key)

# Сохранить в кеш (KEY IDENTIFIER = email!)
await self.cache.keys.set(
    CacheKeyManager.key(key.email),  # ⚠️ email, не id!
    key
)
```

#### 5. Переход в MainMenu

```python
await self.dialog_manager.start(
    MainMenu.main,
    mode=StartMode.RESET_STACK
)
```

### Полный код сценария

```python
async def start(self):
    await self.get_data()

    logger.info("Сценарий создания первого ключа запущен")

    if not self._tariff:
        raise ValueError("Tariff not found")

    try:
        # Шаг 1: Создать пользователя
        tg_id = self.dialog_manager.event.from_user.id
        self._user = await self.create_user(tg_id)
        logger.info(f"User created: {tg_id}")

        # Шаг 2: Создать ключ
        key = await self.create_key.run(
            tariff_id=self._tariff.id,
            user_id=self._user.tg_id,
        )
        logger.info(f"Key created: {key.email}")

        # Шаг 3: Сохранить в БД и кеш
        await self.key_data.insert(key)
        await self.cache.keys.set(
            CacheKeyManager.key(key.email),
            key
        )

        # Шаг 4: Показать профиль
        await self.dialog_manager.start(
            MainMenu.main,
            mode=StartMode.RESET_STACK
        )

    except Exception as e:
        logger.error(f"Error in CreateFerstKeyScenario: {e}", exc_info=True)
        raise
```

---

## Полная диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│ Пользователь                                                │
│ /start [token]                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │  Фаза 1   │
                    │ Middleware│
                    └────┬──────┘
                         │
                    Проверка кеша:
                  ┌──────┬──────────┐
                  │      │          │
           ┌──────▼────┐ │    ┌──────▼──────┐
           │Найден в   │ │    │ Не найден   │
           │кеше       │ │    │ (new user)  │
           │           │ │    │             │
           │registered │ │    └──────┬──────┘
           │_user      │ │           │
           └──────┬────┘ │    ┌──────▼────────┐
                  │      │    │  Фаза 2       │
                  │      │    │ Registration  │
                  │      │    │ Factory       │
                  │      │    └──────┬────────┘
                  │      │           │
                  │      │    ┌──────┴────────┐
                  │      │    │               │
                  │      │ ┌──▼────┐    ┌────▼──┐
                  │      │ │Gift   │    │Unknown│
                  │      │ │Token? │    │Token? │
                  │      │ └──┬────┘    └────┬──┘
                  │      │    │             │
                  │      │ ┌──▼────────┐ ┌──▼─────────┐
                  │      │ │gift       │ │unknown_user│
                  │      │ │activation │ │dialogs     │
                  │      │ │scenario   │ │Register    │
                  │      │ └──┬────────┘ └──┬─────────┘
                  │      │    │             │
           ┌──────▼──────▼────▼─────────────▼─────┐
           │        Фаза 3: Диалоговый флоу       │
           │  - Gift: GiftActivationScenario      │
           │  - Unknown: Register.welcome → ...   │
           │  - Registered: MainMenu.main         │
           └──────────┬──────────────────────────┘
                      │
           ┌──────────▼────────────┐
           │  Фаза 4: CreateFirst  │
           │  KeyScenario          │
           │  1. get_data()        │
           │  2. create_user()     │
           │  3. create_key()      │
           │  4. save to cache     │
           │  5. MainMenu.main     │
           └──────────┬────────────┘
                      │
           ┌──────────▼────────────┐
           │  ✅ Регистрация       │
           │  завершена            │
           │                       │
           │  User + Key в БД      │
           │  User в кеше          │
           │  Key в кеше           │
           └───────────────────────┘
```

---

## Примеры

### Пример 1: Обычная регистрация

```
Пользователь: /start
Bot: "👋 Добро пожаловать в VPN-бот!"
     [Начать регистрацию]

Пользователь: нажимает кнопку
Bot: "📝 ✅ Форма заполнена. Теперь вы можете подать заявку"
     [Отправить заявку]

Пользователь: нажимает кнопку
Bot: "✅ Заявка отправлена! Ожидайте подтверждения администратора"

⏳ После подтверждения (через admin panel):
Bot: "✅ Ваша заявка одобрена! Вот ваш первый VPN-ключ..."
     [Профиль] [Ключи] [Продлить]
```

**Код в middleware:**
```python
registration_result = {
    "success": True,
    "type": "unknown_user"
}
```

---

### Пример 2: Подарочная регистрация

```
Пользователь переходит по ссылке:
https://t.me/MyVPNBot?start=gift_abc123xyz

Bot запускает middleware:
1. Проверка кеша → not found
2. Парсинг токена → "gift_abc123xyz"
3. GiftRegistration.can_handle(token) → True
4. GiftRegistration.register(token) → {
     type: "gift",
     tariff_id: 10,
     from_user_id: 123456,
   }

handlers/start.py → elif type == "gift":
   Запуск GiftActivationScenario

GiftActivationScenario.start():
   1. Создание User
   2. Создание Key (из тарифа подарка)
   3. Сохранение в БД/кеш
   4. Благодарность за подарок
   5. MainMenu.main (профиль с ключом)

Результат: Пользователь сразу получает рабочий ключ! ✅
```

**Данные в middleware:**
```python
registration_result = {
    "success": True,
    "type": "gift",
    "token": "gift_abc123xyz",
    "tariff_id": 10,
    "from_user_id": 123456,
}
```

---

### Пример 3: Зарегистрированный пользователь повторно открывает бот

```
Пользователь: /start
Bot запускает middleware:
1. Проверка кеша → FOUND! (User кешируется на 24ч)
2. registration_result = {success: True, type: "registered_user"}

handlers/start.py → elif type == "registered_user":
   Запуск MainMenu.main (профиль пользователя)

Результат: Пользователь видит свой профиль со своими ключами ✅
```

---

## Интеграция с другими компонентами

### 1. DI контейнер (`services/conteiner/app.py`)

Все зависимости регистрируются один раз:

```python
# В контейнере
container.register(RegistrationFactory, scope=punq.Scope.singleton)
container.register(GiftRegistration, scope=punq.Scope.singleton)
container.register(CreateFerstKeyScenario, factory=..., scope=punq.Scope.transient)
```

### 2. Кеширование пользователей и ключей

```python
# После создания User
await cache.users.set(
    CacheKeyManager.user(tg_id),
    user,
    ttl=86400  # 24 часа
)

# После создания Key (⚠️ используем email как идентификатор!)
await cache.keys.set(
    CacheKeyManager.key(key.email),  # email, не id!
    key,
    ttl=3600   # 1 час
)
```

### 3. 3x-ui интеграция

CreateKey отправляет запрос на панель через XUISession:

```python
# Создание ключа на панели
response = await self.xui_session.inbound.add_user(
    inbound_id=inbound_id,
    email=email,
    password=password,
    traffic_limit=traffic_limit,
    expiry_time=expiry_unix,
)
```

---

## Типичные ошибки и отладка

### ❌ Ошибка: "Пользователь не найден при создании ключа"

**Причина:** User не сохранился в БД перед созданием Key

**Решение:**
```python
# ✅ Правильно: сначала User, потом Key
user = await self.user_data.insert(user)
await self.cache.users.set(CacheKeyManager.user(user.tg_id), user)

key = await self.create_key.run(user_id=user.tg_id)
```

### ❌ Ошибка: "KeyError при сохранении в кеш"

**Причина:** Используется неправильный идентификатор для Key

**Решение:**
```python
# ❌ Неправильно
await cache.keys.set(keys.key(key.id), key)  # Key не имеет .id!

# ✅ Правильно
await cache.keys.set(keys.key(key.email), key)  # Key.email — идентификатор!
```

### ❌ Ошибка: "DEFAULT_PRICING_PLAN это строка, а не int"

**Причина:** Config из env всегда строка, нужно кастовать

**Решение:**
```python
# ❌ Неправильно
tariff_id = DEFAULT_PRICING_PLAN  # "10" (str)
tariff = await self.tariff_data.get_data(tariff_id)  # KeyError!

# ✅ Правильно
tariff_id = int(DEFAULT_PRICING_PLAN)  # 10 (int)
tariff = await self.tariff_data.get_data(tariff_id)  # ✅ Found
```

---

## Тестирование регистрации

### Unit тесты

**Файл:** `tests/middlewares/test_registration_users.py`

```python
async def test_new_user_registration():
    """Тест регистрации нового пользователя"""
    middleware = RegistrationUsersMiddleware()

    # Mock компоненты
    cache_service = AsyncMock(spec=CacheService)
    cache_service.users.get.return_value = None  # Кеш пуст

    event = Mock(spec=Update)
    event.message.text = "/start"
    event.from_user.id = 123456

    data = {
        "cache": cache_service,
        "event_from_user": event.from_user,
    }

    result = await middleware(async_handler, event, data)

    assert data["registration_result"]["type"] == "unknown_user"
```

### Integration тесты

```python
async def test_gift_registration_flow():
    """Полный сценарий подарочной регистрации"""
    # Создать gift_link в БД
    gift = GiftLink(
        token="gift_test_123",
        tariff_id=10,
        sender_tg_id=999999,
    )

    # Проверить распознавание токена
    gift_reg = GiftRegistration(service_data)
    assert await gift_reg.can_handle("gift_test_123") is True

    # Проверить результат регистрации
    result = await gift_reg.register("gift_test_123")
    assert result["type"] == "gift"
    assert result["tariff_id"] == 10
```

---

## Расширение регистрации

### Добавление нового типа регистрации

1. **Создать класс-обработчик:**

```python
# registration/my_registration.py
from registration.base_registration import BaseRegistration

class MyRegistration(BaseRegistration):
    async def can_handle(self, token: str) -> bool:
        # Логика определения подходящего токена
        return token.startswith("my_")

    async def register(self, token: str) -> Dict[str, Any]:
        # Логика регистрации
        return {
            "success": True,
            "type": "my_type",
            "data": {...}
        }
```

2. **Зарегистрировать в контейнере:**

```python
# services/conteiner/app.py
def get_container():
    container.register(MyRegistration, scope=punq.Scope.singleton)
```

3. **Зарегистрировать в middleware:**

```python
# middlewares/registration_users.py
my_registration = container.resolve(MyRegistration)
factory.register_handler(my_registration)
```

4. **Добавить обработку в handlers/start.py:**

```python
elif type_registration == "my_type":
    await my_custom_scenario.start()
```

---

## Ссылки на связанные документы

- [REGISTRATION_MODULE.md](./REGISTRATION_MODULE.md) — структура модуля регистрации
- [STATES_MODULE.md](./STATES_MODULE.md) — FSM-состояния (Register, MainMenu, PaymentState)
- [DIALOGS_MODULE.md](./DIALOGS_MODULE.md) — архитектура диалогов
- [MIDDLEWARES_MODULE.md](./MIDDLEWARES_MODULE.md) — стек middleware
- [services.md](./services.md) — описание сервисов (CreateKey, TrialService)
- [MODELS_MODULE.md](./MODELS_MODULE.md) — модели данных (User, Key, GiftLink)

---

## Контрольный список разработчика

При работе с регистрацией проверьте:

- [ ] Middleware правильно извлекает токен из `/start`
- [ ] RegistrationFactory включает все необходимые обработчики
- [ ] handlers/start.py обрабатывает все типы регистрации
- [ ] User создаётся в БД **перед** Key
- [ ] Key сохраняется в кеш с использованием **email как идентификатора**
- [ ] DEFAULT_PRICING_PLAN кастуется в int из str
- [ ] Dialog переход использует `StartMode.RESET_STACK`
- [ ] Все зависимости инжектируются через контейнер
- [ ] Логирование включает user_id для отладки
- [ ] Тесты покрывают все три типа регистрации
