# Сценарии взаимодействия пользователей с ботом

## 1. Регистрация нового пользователя (без токена)

### Пользовательская часть

```
/start (без токена)
  → RegistrationUsersMiddleware: пользователь не найден в кэше/БД, токена нет
  → handlers/start.py: type="unknown_user" или result=None
  → Register.welcome
```

**Register.welcome** — Приветственное окно
- Message: `WELCOME_MSG` — "Напиши имя или @username того, кто посоветовал"
- Keyboard: `TextInput(id="username_input")` + кнопка "Поддержка"
- Действие: пользователь вводит текст → сохраняется в `dialog_data["username"]` → переход на `Register.sending_registration`

**Register.sending_registration** — Подтверждение заявки
- Message: "Вас пригласил {username}! Форма заполнена."
- Getter: `RegistrationSendingGetter` — читает `username` из `dialog_data`
- Keyboard: кнопка "Подать заявку" + "Поддержка"
- Действие при нажатии "Подать заявку":
  1. Проверка флага в кэше: `cache.users.get(CacheKeyManager.registration_user(tg_id))`
  2. Если флаг **не установлен** — сохраняет `username` в кэш по ключу `registration_user(tg_id)`, отправляет уведомление всем `ADMIN_ID`
  3. Если флаг **уже установлен** — повторное уведомление НЕ отправляется
  4. Пользователь видит alert: "Ваша заявка отправлена администратору! Ожидайте ответа"

**Уведомление админу** содержит:
- ID, имя, username пользователя, кто пригласил
- Кнопка "Добавить пользователя" (`callback_data=addUser_{tg_id}`)
- Кнопка "Отклонить заявку" (`callback_data=rejectUser_{tg_id}`)

**Пользователь НЕ записывается в БД/кэш на этом этапе.**

### Админская часть — одобрение

```
Админ нажимает "Добавить пользователя"
  → handlers/admin.py: callback addUser_{tg_id}
  → on_add_user_request()
  → AdminUserRegistration.user_registration_form
```

**AdminUserRegistration.user_registration_form** — Выбор подключения
- Message: "Новая заявка на регистрацию. ID, приглашён кем. Выберите подключение"
- Getter: `AdminRegistrationGetter` — загружает `tg_id` из `start_data`, inbounds из `cache.inbounds.all()`, имя приглашающего из `CacheKeyManager.registration_user(tg_id)`
- Keyboard: Radio-кнопки с inbounds + "Готово" + "Написать пользователю"
- **Inbounds**: если отсутствуют в кэше — обновляются из 3x-ui панели через `XUISession.get_inbounds()`

**Действие при нажатии "Готово":**
1. Читает `tg_id` из `start_data`, выбранный `inbound_id` из Radio widget
2. Находит `server_id` из выбранного Inbound
3. Создаёт пользователя в БД: `SeverUser.register_user(pool, tg_id=tg_id, server_id=server_id)`
4. Кэширует: `cache.users.set(CacheKeyManager.user(tg_id), new_user)`
5. Сохраняет inbound во временный кэш: `CacheKeyManager.temporary_inbound(tg_id)` — для генерации первого ключа
6. Отправляет пользователю приветственное сообщение `MSG_PREVIEW` с кнопкой "Активировать пробный период" (`callback_data=trial_key`)

**Выбранный inbound — временный**, используется только для генерации первого ключа через `CreateFerstKeyScenario`.

### Админская часть — отклонение

```
Админ нажимает "Отклонить заявку"
  → handlers/admin.py: callback rejectUser_{tg_id}
  → on_reject_user_request()
```

**Действие:**
1. Удаляет флаг из кэша: `cache.users.delete(CacheKeyManager.registration_user(tg_id))` — пользователь сможет подать заявку повторно
2. Отправляет пользователю сообщение об отклонении
3. Отвечает админу: "Заявка отклонена"

---

## 2. Регистрация через gift-токен (автоматическая)

```
/start {gift_token}
  → RegistrationUsersMiddleware: токен извлечён из /start команды
  → RegistrationFactory → GiftRegistration.can_handle() → True
  → result = {type: "gift", token, tariff_id, from_user_id}
  → handlers/start.py: type="gift"
  → GiftActivationScenario.start()
```

**Одобрение админа НЕ требуется.** Пользователь создаётся в БД автоматически.

---

## 3. Регистрация через реферальный токен (автоматическая)

```
/start {referral_token}
  → RegistrationUsersMiddleware: токен извлечён
  → RegistrationFactory → ReferralRegistration (если реализован)
  → Автоматическая регистрация
```

**Одобрение админа НЕ требуется.**

---

## 4. Активация пробного периода

```
Пользователь нажимает "Активировать пробный период" (callback: trial_key)
  → handlers/admin.py: on_trial_key()
  → Instruction.choosing_device
  → Выбор устройства → CreateFerstKeyScenario
  → KeysInit.create_trial
```

**CreateFerstKeyScenario:**
1. Загружает пользователя из кэша
2. Загружает тариф `DEFAULT_PRICING_PLAN` (кастует в `int`)
3. Создаёт trial-ключ через 3x-ui API
4. Устанавливает `trial = -1` (использован)
5. Отображает ключ с кнопками копирования/скачивания

---

## 5. Просмотр профиля

```
/profile
  → handlers/start.py: send_massage_user_start()
  → Проверка кэша: cache.users.get(CacheKeyManager.user(tg_id))
```

| Условие | Переход |
|---------|---------|
| Пользователь не найден | `Register.welcome` |
| `trial == 0` (доступен) | `MainMenu.welcome` |
| `trial != 0` (использован) | `MainMenu.main` |

---

## 6. Управление ключами

```
MainMenu.main → "Мои ключи"
  → KeysInit.list (список ключей)
  → KeysInit.key (детали ключа)
```

**Действия с ключом:**
- Копировать — копирование ключа
- Скачать приложение — ссылки на App Store / Play Store
- Продлить (trial) → `PaymentState.view_tariff` (выбор тарифа)
- Продлить (платный) → `PaymentState.setting_pay` (настройка оплаты)
- Удалить → `KeysInit.confirmation_delete_key`

---

## 7. Оплата и продление

```
PaymentState.view_tariff → выбор тарифа
  → PaymentState.setting_pay → кол-во месяцев, итого
  → PaymentState.form_pay → оплата через YooKassa
```

**После оплаты (webhook):**
- `PaymentRouter` определяет тип: `create_key|{tariff_id}` или `renew_key|{email}`
- `KeyCreationService` — создание нового ключа
- `KeyRenewalService` — продление существующего

---

## 8. Подарочные ссылки

```
MainMenu.main → "Подарить ключ"
  → GiftStates.main — генерация и отображение gift-ссылки
```

Получатель переходит по ссылке → Сценарий 2 (автоматическая регистрация).

---

## 9. Админ-панель

```
MainMenu.main → "Администратор" (видна только ADMIN_ID)
  → AdminManager.main
```

### 9.1 Статистика
```
AdminManager.main → "Статистика пользователей"
  → AdminManager.static_user
  → Сегментация ключей (all/24h/expired/active/trial)
  → AdminManager.key_list → AdminManager.key_details
```

### 9.2 Поиск пользователей
```
AdminManager.main → "Поиск"
  → AdminSearchManagementSG.main
  → Поиск по Telegram ID / Email
  → AdminSearchManagementSG.profile_user
```

**Действия с профилем:** восстановить trial, удалить пользователя, просмотреть ключи.

### 9.3 Управление ключами (админ)
```
AdminManager.key_details
  → "Удалить ключ" → AdminKeyDeleteSG.confirm
  → "Изменить дату" → AdminKeyChangeDateSG.pick_date → confirm
  → "Изменить тариф" → AdminKeyChangeTariffSG.pick_tariff → confirm
```

### 9.4 Массовая рассылка
```
AdminManager.main → "Массовая рассылка"
  → AdminMassMailing.receiving_message → ввод текста
  → AdminMassMailing.confirmation → предпросмотр + подтверждение
```

### 9.5 Синхронизация
```
AdminManager.main → "Синхронизация"
  → click_sync_cache() → DatabaseSynchronizer
  → Обновление кэша из 3x-ui + БД
```

---

## 10. Уведомления (фоновые)

### TrialReminderFunnel (каждый час)
Пользователи с trial-ключами, истекающими в 24ч → inline-сообщение:
- "Подключиться" (`connect_vpn`) → инструкции
- "Активировать" (`activate_stock`) → создание trial
- "Профиль" (`profile`) → главное меню

### Обработчики callback уведомлений (`handlers/notifications.py`)

| Callback | Действие |
|----------|----------|
| `renew_key\|{email}` | Продление ключа (trial → view_tariff, paid → setting_pay) |
| `activate_stock` | Активация trial через `CreateFerstKeyScenario` |
| `connect_vpn` | Инструкции подключения |
| `profile` | Открытие профиля |

---

## Ключевые файлы по сценариям

| Компонент | Файл |
|-----------|------|
| Middleware регистрации | `middlewares/registration_users.py` |
| Стартовый handler | `handlers/start.py` |
| Admin handler | `handlers/admin.py` |
| Notification handlers | `handlers/notifications.py` |
| Состояния Register | `states/registrate.py` |
| Состояния Admin | `states/admin.py` |
| Виджеты Register | `dialogs/windows/widgets/{message,keybord}/register/` |
| Виджеты AdminRegistration | `dialogs/windows/widgets/{message,keybord}/admin/registration.py` |
| Getter Register | `dialogs/windows/getters/register/sending.py` |
| Getter AdminRegistration | `dialogs/windows/getters/admin/registration.py` |
| Window configs | `dialogs/windows/__init__.py` |
| Приветственные сообщения | `dialogs/messages/users/welcom/first_msg.py` |
| CacheKeyManager | `services/cache/key_manager.py` |
| XUI client | `client.py` |
