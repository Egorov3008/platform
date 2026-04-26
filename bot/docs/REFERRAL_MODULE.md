# Реферальная программа

Модуль реферальной системы: генерация ссылок, регистрация рефералов, начисление бонусов, UI-диалоги, уведомления.

## Оглавление

- [Общая схема](#общая-схема)
- [Модели данных](#модели-данных)
- [Генерация ссылок](#генерация-ссылок)
- [Регистрация реферала](#регистрация-реферала)
- [Начисление бонусов](#начисление-бонусов)
- [UI-диалоги](#ui-диалоги)
- [Уведомления](#уведомления)
- [Конфигурация](#конфигурация)
- [Тесты](#тесты)
- [Ключевые файлы](#ключевые-файлы)

---

## Общая схема

```
Реферер                          Реферал (новый пользователь)
   │                                      │
   │ 1. Открывает "Реферальная            │
   │    программа" в профиле              │
   │                                      │
   │ 2. Генерирует ссылку                 │
   │    ref_a3f9c1d2e4b7                  │
   │                                      │
   │ 3. Отправляет ссылку ──────────────► │
   │    t.me/bot?start=ref_...            │
   │                                      │ 4. Переход по ссылке
   │                                      │    → /start ref_a3f9c1d2e4b7
   │                                      │
   │                                      │ 5. Middleware: распознаёт токен
   │                                      │    → ReferralRegistration
   │                                      │
   │                                      │ 6. Данные в temp-кеш (TTL 7д)
   │                                      │    referral_{tg_id}
   │                                      │
   │                                      │ 7. Регистрация (welcome → done)
   │                                      │    → User.referral_id = реферер
   │                                      │    → ReferralRedemption запись
   │                                      │
   │                                      │ 8. Первая оплата
   │                                      │
   │ 9. Бонус 10% от суммы ◄──────────── │
   │    → ReferralReward запись           │
   │    → User.check_referral = True      │
```

---

## Модели данных

### Таблицы БД

| Таблица | Модель | Назначение |
|---------|--------|------------|
| `referral_links` | `ReferralLink` | Реферальные ссылки пользователей |
| `referral_redemptions` | `ReferralRedemption` | Факты перехода по ссылке |
| `referral_rewards` | `ReferralReward` | Начисленные бонусы |

### ReferralLink

```python
# models/referrals/referral_link.py
@dataclass
class ReferralLink:
    referrer_tg_id: int              # tg_id владельца ссылки
    token: str                       # уникальный токен (ref_xxxxxxxxxxxx)
    created_at: Optional[datetime]   # auto: datetime.utcnow()
    id: Optional[int]                # SERIAL, исключён из INSERT
```

### ReferralRedemption

```python
# models/referrals/referral_redemption.py
@dataclass
class ReferralRedemption:
    referral_link_id: int            # FK → referral_links.id
    referred_tg_id: int              # tg_id нового пользователя
    redeemed_at: Optional[datetime]  # auto: datetime.utcnow()
    id: Optional[int]                # SERIAL, исключён из INSERT
```

### ReferralReward

```python
# models/referrals/referral_reward.py
@dataclass
class ReferralReward:
    referrer_tg_id: int              # tg_id получателя бонуса
    reward_type: str                 # тип: "discount_percent"
    reward_value: str                # значение: "50.0" (сумма в рублях)
    awarded_at: Optional[datetime]   # auto: datetime.utcnow()
    is_claimed: bool = False         # использован ли бонус
    id: Optional[int]                # SERIAL, исключён из INSERT
```

### Поля в модели User

| Поле | Тип | Назначение |
|------|-----|------------|
| `referral_id` | `Optional[int]` | `tg_id` пригласившего пользователя |
| `check_referral` | `bool` | Флаг: бонус уже начислен (идемпотентность) |

---

## Генерация ссылок

**Сервис:** `services/core/referral/link_generator.py` → `ReferralLinkGenerator`

### Формат токена

```
ref_ + 12 hex-символов UUID4
Пример: ref_a3f9c1d2e4b7
```

### Формат ссылки

```
https://t.me/{BOT_NAME}?start=ref_a3f9c1d2e4b7
```

### API

```python
class ReferralLinkGenerator:
    async def get_or_create(self, conn: asyncpg.Pool, tg_id: int) -> ReferralLink
        # Возвращает существующую ссылку или создаёт новую.
        # Одна ссылка на пользователя.

    def get_share_url(self, token: str) -> str
        # Формирует полный URL: https://t.me/{BOT_NAME}?start={token}
```

Ссылки кешируются при старте через `LoadingService` с ключом `referral_link_{token}`.

---

## Регистрация реферала

### Поток обработки

#### 1. Middleware (`middlewares/registration_users.py`)

`RegistrationUsersMiddleware` перехватывает `/start <token>`:

1. Проверяет, известен ли пользователь (кеш → БД)
2. Извлекает токен из команды `/start`
3. Передаёт токен в `RegistrationFactory`
4. `ReferralRegistration.can_handle(token)` — ищет токен в `referral_links`
5. Результат → `data["registration_result"]` с `type="referral"`

#### 2. Handler (`handlers/start.py`)

При `type == "referral"`:

```python
await cache.users.temporary_set(
    f"referral_{tg_id}",
    ttl=timedelta(days=7),
    referrer_tg_id=result.get("referrer_tg_id"),
    referral_link_id=result.get("referral_link_id"),
)
await dialog_manager.start(Register.welcome, mode=StartMode.RESET_STACK)
```

Реферальные данные сохраняются во временный кеш (TTL 7 дней) на время регистрации.

#### 3. Завершение регистрации

При `AdminRegistrationKeyboard._on_done()`:

1. Читает `referral_{tg_id}` из временного кеша
2. Устанавливает `User.referral_id = referrer_tg_id`
3. Создаёт запись `ReferralRedemption(referral_link_id, referred_tg_id)`

### ReferralRegistration

```python
# registration/referral_registration.py
class ReferralRegistration(BaseRegistration):
    async def can_handle(self, token: str) -> bool
        # True если токен найден в referral_links

    async def register(self, token: str) -> Dict[str, Any]
        # Возвращает: {success, type, token, referrer_tg_id, referral_link_id}
```

---

## Начисление бонусов

**Сервис:** `services/core/referral/bonus_service.py` → `ReferralBonusService`

### Логика

```python
class ReferralBonusService:
    async def process_referral_bonus(
        self, conn: asyncpg.Pool, referred_tg_id: int, payment_amount: float
    ) -> None:
```

1. Загрузить пользователя по `referred_tg_id`
2. **Пропустить если:** `referral_id is None` или `check_referral is True`
3. Рассчитать бонус: `payment_amount × 10%` (уровень 1)
4. Создать `ReferralReward` для пригласившего
5. Установить `user.check_referral = True` (одноразовый бонус)

### Интеграция с платежами

`PaymentRouter.route()` вызывает `bonus_service.process_referral_bonus()` после успешной обработки платежа (создание или продление ключа). Ошибки логируются как warning, но не прерывают платёж.

### Пример расчёта

| Сумма платежа | Процент | Бонус реферера |
|---------------|---------|----------------|
| 300 ₽ | 10% | 30.0 ₽ |
| 500 ₽ | 10% | 50.0 ₽ |
| 1000 ₽ | 10% | 100.0 ₽ |

### Ограничения

- Бонус начисляется **один раз** — только при первой оплате реферала
- Флаг `check_referral` гарантирует идемпотентность
- Уровни 2 и 3 определены в конфиге, но **не реализованы**

---

## UI-диалоги

### FSM-состояния

```python
# states/referral.py
class ReferralSistem(StatesGroup):
    main = State()           # Главное окно реферальной программы
    generate_form = State()  # Определено, но не используется
```

### Точка входа

Кнопка «👥 Реферальная программа» в профиле пользователя (`dialogs/windows/widgets/keybord/profile/main.py`).

### Окно `ReferralSistem.main`

| Компонент | Класс | Файл |
|-----------|-------|------|
| Сообщение | `ReferralMainMessage` | `dialogs/windows/widgets/message/referral/main.py` |
| Клавиатура | `ReferralMainKeyboard` | `dialogs/windows/widgets/keybord/referral/main.py` |
| Геттер | `ReferralMainGetter` | `dialogs/windows/getters/referral/main.py` |

### Сообщение (два варианта)

**Ссылка есть** (`has_link = True`):
```
👥 Реферальная программа

🔗 Ваша ссылка: {share_url}
👤 Приглашённых: {referral_count}
🎁 Бонусов: {rewards_count}

Приглашайте друзей и получайте 10% от суммы его платежа!
```

**Ссылки нет** (`has_link = False`):
```
👥 Реферальная программа

Создайте реферальную ссылку и приглашайте друзей!
```

### Клавиатура

| Условие | Кнопки |
|---------|--------|
| `has_link` | 📋 Скопировать ссылку (CopyText) |
| `no_link` | 🔗 Создать реферальную ссылку (Button → `_on_generate_link`) |
| Всегда | 👤 В личный кабинет (Start → MainMenu.main) |

### Данные геттера

`ReferralMainGetter.get_data()` возвращает:

| Ключ | Тип | Описание |
|------|-----|----------|
| `has_link` | `bool` | Есть ли ссылка у пользователя |
| `no_link` | `bool` | Инверсия `has_link` |
| `share_url` | `str` | Полная ссылка для шаринга |
| `referral_count` | `int` | Количество `ReferralRedemption` записей |
| `rewards_count` | `int` | Количество `ReferralReward` записей |

---

## Уведомления

**Воронка:** `services/notification/funnels/referral_bonus.py` → `ReferralBonusFunnel`

### Назначение

Отправляет приветственное сообщение пользователям, пришедшим по реферальной ссылке, но ещё не активировавшим пробный период.

### Условия отправки (`should_send`)

| Условие | Описание |
|---------|----------|
| `user.referral_id is not None` | Пользователь пришёл по реферальной ссылке |
| `user.trial == 0` | Пробный период не активирован |
| Не отправлялось ранее | Дедупликация с TTL 30 дней |

### Текст уведомления

```
🎉 Вас пригласил друг!

Активируйте пробный период и получите:
🆓 7 дней бесплатного пользования
📦 10 ГБ трафика
⚡️ Полный доступ ко всем функциям

Начните прямо сейчас! 👇
```

**Кнопки:** «🎁 Активировать пробный период» (`activate_stock`), «👤 Личный кабинет» (`profile`).

---

## Конфигурация

### Переменные окружения

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `BOT_NAME` | Имя бота для deep link | `my_vpn_bot` |

### Константы (`config.py`)

```python
REFERRAL_BONUS_PERCENTAGES = {
    "1": "0.10",  # 10% — уровень 1 (активен)
    "2": "0.05",  # 5%  — уровень 2 (не реализован)
    "3": "0.02",  # 2%  — уровень 3 (не реализован)
}
```

---

## Тесты

```bash
# Все тесты реферальной системы
pytest tests/models/test_referral_models.py
pytest tests/registration/test_referral_registration.py
pytest tests/services/core/referral/

# Конкретные модули
pytest tests/services/core/referral/test_bonus_service.py
pytest tests/services/core/referral/test_link_generator.py
```

### Покрытие

| Файл тестов | Что тестируется |
|-------------|-----------------|
| `test_referral_models.py` | Создание моделей, `to_dict()` / `from_dict()`, `_DB_FIELDS`, auto-datetime |
| `test_referral_registration.py` | `can_handle()`, `register()` — успех и ошибка |
| `test_bonus_service.py` | Расчёт бонуса, идемпотентность (`check_referral`), skip-сценарии |
| `test_link_generator.py` | `get_or_create()`, формат токена, `get_share_url()`, уникальность |
| `test_funnels.py` | `ReferralBonusFunnel.should_send()` — условия и дедупликация |

---

## Ключевые файлы

### Модели
- `models/referrals/referral_link.py`
- `models/referrals/referral_redemption.py`
- `models/referrals/referral_reward.py`
- `models/users/user.py` — поля `referral_id`, `check_referral`

### Сервисы
- `services/core/referral/link_generator.py` — `ReferralLinkGenerator`
- `services/core/referral/bonus_service.py` — `ReferralBonusService`

### Регистрация
- `registration/referral_registration.py` — `ReferralRegistration`
- `registration/registration_factory.py` — `RegistrationFactory`
- `middlewares/registration_users.py` — `RegistrationUsersMiddleware`
- `handlers/start.py` — обработка `/start` с реферальным токеном

### Диалоги
- `states/referral.py` — `ReferralSistem`
- `dialogs/windows/widgets/message/referral/main.py` — `ReferralMainMessage`
- `dialogs/windows/widgets/keybord/referral/main.py` — `ReferralMainKeyboard`
- `dialogs/windows/getters/referral/main.py` — `ReferralMainGetter`

### Уведомления
- `services/notification/funnels/referral_bonus.py` — `ReferralBonusFunnel`

### Платежи
- `services/core/payment/router.py` — вызов `process_referral_bonus()` после оплаты

### Тесты
- `tests/models/test_referral_models.py`
- `tests/registration/test_referral_registration.py`
- `tests/services/core/referral/test_bonus_service.py`
- `tests/services/core/referral/test_link_generator.py`
