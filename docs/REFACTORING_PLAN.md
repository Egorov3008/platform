# План рефакторинга VPN Platform

**Цель:** Устранить выявленные антипаттерны, повысить тестируемость и поддерживаемость кода.

**Принципы:**
1. Каждый этап завершается passing tests + коммитом
2. Коммиты атомарны — можно сделать rollback без влияния на другие изменения
3. Сначала тесты, потом рефакторинг (red-green-refactor)
4. Сохраняется обратная совместимость API

---

## Этап 0: Подготовка инфраструктуры тестирования

**Цель:** Убедиться, что тесты запускаются и проходят перед началом изменений.

### Задачи:
- [ ] Запустить все тесты backend
- [ ] Запустить все тесты bot
- [ ] Зафиксировать baseline coverage

### Коммит:
```
test: baseline test suite verification

- Verify all existing tests pass before refactoring
- Document test coverage baseline
```

---

## Этап 1: Fix race condition в scheduler (P0, критично)

**Файлы:** `backend/background/scheduler.py`

**Проблема:** Глобальный флаг `_sync_in_progress` проверяется ДО входа в lock.

### Задачи:
- [ ] 1.1 Написать тест на race condition
- [ ] 1.2 Рефакторинг: инкапсуляция состояния в класс
- [ ] 1.3 Тесты на параллельные запуски
- [ ] 1.4 Passing tests + коммит

### Тесты:
```python
# backend/tests/unit/test_scheduler_race_condition.py
async def test_concurrent_sync_runs_only_once():
    """Две одновременные попытки sync → выполняется только одна."""
```

### Коммит:
```
fix(backend): eliminate race condition in scheduler sync

- Move _sync_in_progress check inside async lock
- Encapsulate sync state in SyncScheduler class
- Add regression test for concurrent sync attempts
```

---

## Этап 2: Исправление spelling `conteiner` → `container` (P3)

**Файлы:** `bot/services/conteiner/` → `bot/services/container/`

### Задачи:
- [ ] 2.1 Создать `bot/services/container/` с правильным spelling
- [ ] 2.2 Перенести файлы с обновлением импортов внутри пакета
- [ ] 2.3 Обновить все внешние импорты
- [ ] 2.4 Запустить тесты bot
- [ ] 2.5 Удалить старый пакет

### Тесты:
```bash
cd bot && pytest tests/services/conteiner/  # Переименовать в container
```

### Коммит:
```
refactor(bot): fix spelling 'conteiner' → 'container'

- Rename package directory
- Update all imports across codebase
- No functional changes
```

---

## Этап 3: Выделение абстракции INotifier (P0, для тестируемости)

**Файлы:** 
- `backend/services/core/payment/creation_service.py`
- `backend/services/core/payment/renewal_service.py`
- `backend/bot_project.py` (новый)

### Задачи:
- [ ] 3.1 Создать `backend/services/core/notifications/protocols.py` с `INotifier`
- [ ] 3.2 Создать `backend/bot_project.py` с `TelegramBotNotifier`
- [ ] 3.3 Обновить `KeyCreationService` для инъекции notifier
- [ ] 3.4 Обновить `KeyRenewalService` для инъекции notifier
- [ ] 3.5 Обновить фабрику `build_payment_router`
- [ ] 3.6 Тесты с моком notifier

### Тесты:
```python
# backend/tests/unit/test_key_creation_service.py
async def test_key_creation_calls_notifier(mock_notifier):
    """KeyCreationService вызывает notifier.send_key_created()."""
```

### Коммит:
```
refactor(backend): extract INotifier for decoupled notifications

- Add INotifier protocol in services/core/notifications/
- Implement TelegramBotNotifier using httpx
- Inject notifier into KeyCreationService and KeyRenewalService
- Remove direct aiogram dependency from payment services
```

---

## Этап 4: Typed DTO для API ответов (P1)

**Файлы:** `bot/api/backend_client.py`, `bot/api/schemas.py`

### Задачи:
- [ ] 4.1 Создать dataclass DTO в `bot/api/schemas.py`
- [ ] 4.2 Обновить `BackendAPIClient` для возврата DTO вместо dict
- [ ] 4.3 Обновить callers для работы с DTO
- [ ] 4.4 Тесты на type safety

### DTO:
```python
@dataclass
class UserDTO:
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance: float
    # ...

@dataclass
class TariffDTO:
    id: int
    name: str
    amount: float
    # ...
```

### Коммит:
```
feat(bot): add typed DTOs for BackendAPIClient responses

- Replace Optional[dict] with typed dataclasses
- Add UserDTO, TariffDTO, KeyDTO, PaymentDTO
- Update all callers to use typed access
```

---

## Этап 5: Circuit breaker для внешних зависимостей (P2)

**Файлы:** `bot/api/backend_client.py`, `backend/client.py`

### Задачи:
- [ ] 5.1 Установить `pybreaker` или реализовать свой circuit breaker
- [ ] 5.2 Обернуть вызовы backend API
- [ ] 5.3 Обернуть вызовы XUI API
- [ ] 5.4 Тесты на circuit breaker states

### Тесты:
```python
# bot/tests/api/test_backend_client_circuit_breaker.py
async def test_circuit_breaker_opens_after_failures():
    """Circuit breaker открывается после N ошибок."""
```

### Коммит:
```
feat: add circuit breaker for external API calls

- Add pybreaker dependency
- Wrap BackendAPIClient calls with circuit breaker
- Wrap XUI API calls with circuit breaker
- Add tests for circuit breaker state transitions
```

---

## Этап 6: Consolidation конфигурации (P2)

**Файлы:** 
- `shared/config/__init__.py` (новый)
- `backend/config.py`
- `bot/config.py`

### Задачи:
- [ ] 6.1 Создать пакет `shared/config/`
- [ ] 6.2 Вынести общие настройки (YooKassa, trial_time, limit_ip)
- [ ] 6.3 Обновить backend для импорта из shared
- [ ] 6.4 Обновить bot для импорта из shared
- [ ] 6.5 Тесты на загрузку конфига

### Коммит:
```
refactor: consolidate shared configuration

- Create shared/config package with CoreSettings
- Move common settings (YooKassa, trial, limits) to shared
- Update backend and bot to import from shared
- Remove duplicate configuration
```

---

## Этап 7: Разделение XUISession на сервисы (P2)

**Файлы:** `backend/client.py` → `backend/services/xui/`

### Задачи:
- [ ] 7.1 Создать `backend/services/xui/auth.py` (XUIAuthService)
- [ ] 7.2 Создать `backend/services/xui/client.py` (XUIClientService)
- [ ] 7.3 Создать `backend/services/xui/inbound.py` (XUIInboundService)
- [ ] 7.4 Создать `backend/services/xui/traffic.py` (XUITrafficService)
- [ ] 7.5 Обновить XUISession для делегирования
- [ ] 7.6 Тесты на каждый сервис отдельно

### Коммит:
```
refactor(backend): decompose XUISession into focused services

- Extract XUIAuthService for authentication/CSRF
- Extract XUIClientService for CRUD operations
- Extract XUIInboundService for inbound management
- Extract XUITrafficService for traffic operations
- XUISession now orchestrates, not implements
```

---

## Этап 8: Устранение глобального состояния (P1)

**Файлы:** `bot/config.py`, `backend/background/scheduler.py`

### Задачи:
- [ ] 8.1 Создать `BotConfig` dataclass
- [ ] 8.2 Создать `SyncScheduler` класс вместо глобальных функций
- [ ] 8.3 Обновить DI контейнер для регистрации синглтонов
- [ ] 8.4 Тесты на изолированное состояние

### Коммит:
```
refactor: eliminate global state

- Encapsulate bot config in BotConfig dataclass
- Replace global scheduler functions with SyncScheduler class
- Register services as singletons in DI container
- Add tests for state isolation
```

---

## Этап 9: Event-driven архитектура для PaymentRouter (P3)

**Файлы:** `backend/services/core/payment/router.py`

### Задачи:
- [ ] 9.1 Создать `backend/services/core/events.py` с EventBus
- [ ] 9.2 Определить события: PaymentSucceeded, KeyCreated, KeyRenewed
- [ ] 9.3 Обновить PaymentRouter для публикации событий
- [ ] 9.4 ReferralBonusService подписывается на PaymentSucceeded
- [ ] 9.5 Тесты на event flow

### Коммит:
```
refactor(backend): event-driven payment processing

- Add EventBus for decoupled event handling
- Define PaymentSucceeded, KeyCreated, KeyRenewed events
- PaymentRouter publishes events instead of calling handlers
- ReferralBonusService subscribes to PaymentSucceeded
```

---

## Этап 10: Финальная верификация

### Задачи:
- [ ] 10.1 Запустить все тесты
- [ ] 10.2 Запустить линтеры
- [ ] 10.3 E2E тесты (если есть)
- [ ] 10.4 Документирование изменений

### Коммит:
```
chore: final refactoring verification

- All tests passing
- Linters clean
- Documentation updated
```

---

## Rollback Instructions

Для отката любого этапа:

```bash
# Откат к конкретному коммиту
git revert <commit-hash>

# Или reset если коммиты еще не pushed
git reset --hard <previous-commit>
```

### Критические точки отката:
1. После Этапа 1 — scheduler стабилен, можно тестировать остальное
2. После Этапа 3 — notification decoupled, тесты изолированы
3. После Этапа 8 — глобальное состояние устранено

---

## Метрики успеха

| Метрика | Before | Target |
|---------|--------|--------|
| Test coverage | ~60% | ~80% |
| Cyclomatic complexity (avg) | 15 | <10 |
| File size (max lines) | 946 (client.py) | <400 |
| Direct dependencies | Tight | Loose (protocols) |
| Global state vars | 20+ | 0 |

---

## Timeline (оценка)

| Этап | Оценка | Приоритет |
|------|--------|-----------|
| 0. Подготовка | 30 мин | Must |
| 1. Scheduler race | 2 часа | P0 |
| 2. Spelling fix | 1 час | P3 |
| 3. INotifier | 4 часа | P0 |
| 4. Typed DTOs | 3 часа | P1 |
| 5. Circuit breaker | 3 часа | P2 |
| 6. Config consolidation | 2 часа | P2 |
| 7. XUISession split | 8 часов | P2 |
| 8. Global state | 4 часа | P1 |
| 9. Event-driven | 4 часа | P3 |
| 10. Verification | 1 час | Must |

**Итого:** ~32 часа (~4 рабочих дня)
