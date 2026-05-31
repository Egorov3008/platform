# Notification Module (`services/notification/`) ❌ Переехал в backend

> ⚠️ **ВАЖНО:** Весь модуль `services/notification/` (воронки, менеджер, message_builder, keyboard_builder, rate_limiter, routing)
> **удалён из бота** и переехал в `backend/`. Воронки запускаются через `backend/background/scheduler.py` (APScheduler, каждый час).
> Бот по-прежнему получает уведомления через `backend/bot_project.py` (httpx → Bot API).

## 📖 Оглавление

1. [Обзор](#обзор)
2. [Архитектура](#архитектура)
3. [Компоненты](#компоненты)
4. [Создание воронок](#создание-воронок)
5. [Интеграция](#интеграция)
6. [Примеры](#примеры)
7. [Настройка](#настройка)
8. [Тестирование](#тестирование)

---

## Обзор

**Notification Module** — система отправки целевых уведомлений пользователям через воронки (funnels). Каждая воронка:
- Определяет группу пользователей (по сегментам ключей)
- Проверяет условия отправки (should_send)
- Отправляет персонализированное сообщение

**Статус:** ✅ Полностью переписано (2026-03-03)

**Основные возможности:**
- ✅ Rate limiting (25 msg/s глобально, 1.1s per-user)
- ✅ Временные окна отправки (9-23 часа)
- ✅ Дедупликация уведомлений
- ✅ Сегментация по типам ключей
- ✅ Отчёты о запусках воронок
- ✅ Интеграция с CacheService

---

## Архитектура

### Диаграмма потока

```
┌─────────────────────────────────────────────────────────┐
│ FunnelManager.run_cycle(bot)                           │
├─────────────────────────────────────────────────────────┤
│ 1. Загрузить users из CacheService                      │
│ 2. Проверить SENDING_HOUR_WINDOW (9-23)               │
│ 3. Для каждой воронки:                                 │
│    ├─ Пре-фильтровать по сегментам KEY_SEGMENT_TO_FUNNEL
│    ├─ Загрузить keys для пользователей                 │
│    ├─ Для каждого пользователя:                        │
│    │  ├─ Создать NotificationContext                   │
│    │  ├─ Вызвать should_send(ctx)                      │
│    │  └─ Если true: процесс(bot, ctx) + rate_limit    │
│    └─ Добавить результаты в FunnelRunReport            │
│ 4. Вернуть FunnelRunReport                             │
└─────────────────────────────────────────────────────────┘
```

### Структура модуля

```
services/notification/
├── __init__.py              # Экспорт: FunnelManager, RateLimiter
├── models.py                # Data models
│   ├── NotificationContext  # Контекст для should_send/process
│   ├── NotificationResult   # Результат отправки одного сообщения
│   └── FunnelRunReport      # Итоговый отчёт воронки
├── protocols.py             # Интерфейсы
│   └── NotificationFunnelProtocol  # Контракт для воронок
├── rate_limiter.py          # Rate limiting (token-bucket)
│   └── RateLimiter          # Ограничение 25 msg/s + 1.1s per-user
├── routing.py               # Маршрутизация
│   ├── KEY_SEGMENT_TO_FUNNEL   # Mapping сегментов → воронки
│   ├── SENDING_HOUR_WINDOW     # (9, 23) — время отправки
│   └── UserFunnelType          # Enum типов пользовательских воронок
├── core.py                  # Legacy типы (FunnelType, UserSegment)
├── manager.py               # Главный оркестратор
│   └── FunnelManager        # run_cycle(bot) → FunnelRunReport
└── funnels/                 # Конкретные реализации
    ├── __init__.py
    ├── key_expiry.py        # KeyExpiryFunnel (истечение ключей)
    ├── trial_reminder.py    # TrialReminderFunnel (trial не использован)
    ├── cold_lead_engagement.py  # ColdLeadFunnel (холодные лиды)
    └── referral_bonus.py    # ReferralBonusFunnel (реферальный бонус)

utils/
├── cache_helpers.py         # NotificationDedupeCache (дедупликация)
```

---

## Компоненты

### 1. NotificationContext

**Назначение:** Контекст для проверки `should_send()` и выполнения `process()`

```python
from dataclasses import dataclass
from typing import Optional, List
from models import User, Key

@dataclass
class NotificationContext:
    """Контекст для воронки"""
    user: User              # Пользователь
    keys: List[Key]         # Все ключи пользователя
    segment_keys: List[Key] # Ключи в текущем сегменте
    funnel_id: str          # ID воронки (key_expiry_24h, trial_unused и т.д.)
    timestamp: datetime     # Время проверки
```

**Использование в воронке:**

```python
async def should_send(self, ctx: NotificationContext) -> bool:
    # ctx.user.tg_id — ID Telegram пользователя
    # ctx.segment_keys — ключи в целевом сегменте
    # ctx.funnel_id — ID текущей воронки

    if not ctx.segment_keys:
        return False  # Нет ключей в сегменте

    key = ctx.segment_keys[0]
    # Проверить кастомную логику...
    return True
```

### 2. NotificationResult

**Назначение:** Результат отправки одного сообщения

```python
@dataclass
class NotificationResult:
    """Результат отправки сообщения"""
    user_id: int                # tg_id пользователя
    funnel_id: str              # ID воронки
    success: bool               # Успешно ли отправлено
    message_id: Optional[int]   # ID отправленного сообщения (если успешно)
    error: Optional[str]        # Ошибка (если failed)
    sent_at: datetime           # Время отправки
    duration_ms: float          # Время выполнения (ms)
```

### 3. FunnelRunReport

**Назначение:** Итоговый отчёт о работе одной воронки

```python
@dataclass
class FunnelRunReport:
    """Отчёт о работе воронки"""
    funnel_id: str                      # ID воронки
    total_users_checked: int            # Всего проверено пользователей
    total_should_send: int              # Условие should_send=true
    total_sent: int                     # Успешно отправлено
    total_failed: int                   # Ошибок отправки
    results: List[NotificationResult]   # Детальные результаты
    started_at: datetime                # Начало работы
    finished_at: datetime               # Конец работы
    duration_ms: float                  # Общее время (ms)

    @property
    def success_rate(self) -> float:
        """Процент успешно отправленных"""
        if self.total_should_send == 0:
            return 0.0
        return (self.total_sent / self.total_should_send) * 100
```

### 4. RateLimiter

**Назначение:** Ограничение частоты отправки сообщений

```python
from services.notification.rate_limiter import RateLimiter

rate_limiter = RateLimiter(
    global_rate=25,         # 25 сообщений в секунду
    user_delay_ms=1100      # 1.1 секунды между сообщениями одному пользователю
)

# Проверка лимита
if await rate_limiter.check_limit(user_id=123):
    # Можно отправить
    await bot.send_message(user_id, "Сообщение...")
    await rate_limiter.add_sent(user_id)
else:
    # Лимит превышен
    pass
```

**Особенности:**
- Token-bucket алгоритм
- Глобальный лимит: 25 msg/s
- Персональный лимит: минимум 1.1s между сообщениями одному пользователю

### 5. NotificationFunnelProtocol

**Назначение:** Интерфейс для всех воронок

```python
from typing import Protocol
from services.notification.models import NotificationContext, NotificationResult

class NotificationFunnelProtocol(Protocol):
    """Контракт для всех воронок"""

    funnel_id: str  # Уникальный ID воронки

    async def should_send(self, ctx: NotificationContext) -> bool:
        """Проверить нужно ли отправлять сообщение"""
        ...

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        """Отправить сообщение и вернуть результат"""
        ...
```

### 6. KEY_SEGMENT_TO_FUNNEL

**Назначение:** Маппинг сегментов ключей на воронки

```python
from services.notification.routing import KEY_SEGMENT_TO_FUNNEL

# Словарь: KeySegment → воронка, которая обрабатывает этот сегмент
KEY_SEGMENT_TO_FUNNEL = {
    KeySegment.EXPIRING_24H: "key_expiry_24h",
    KeySegment.TRIAL: "trial_unused",
    KeySegment.ALL: "cold_lead",  # Воронка холодных лидов
}
```

**Используется в FunnelManager для пре-фильтрации:**

```python
# Только ключи, истекающие в 24 часа
if funnel.funnel_id == "key_expiry_24h":
    segment_keys = await segmentation_service.get_expiring_24h(all_keys)
```

---

## Создание воронок

### Шаблон воронки

```python
# services/notification/funnels/my_funnel.py

from typing import List, Optional
from datetime import datetime
from aiogram import Bot

from models import User, Key
from services.cache.service import CacheService
from services.notification.models import NotificationContext, NotificationResult
from services.notification.rate_limiter import RateLimiter


class MyFunnel:
    """Описание воронки"""

    funnel_id = "my_funnel"  # Уникальный ID

    def __init__(
        self,
        cache: CacheService,
        rate_limiter: RateLimiter,
        # Другие зависимости...
    ):
        self.cache = cache
        self.rate_limiter = rate_limiter

    async def should_send(self, ctx: NotificationContext) -> bool:
        """
        Проверить нужно ли отправлять сообщение.

        Args:
            ctx: NotificationContext с данными пользователя и ключей

        Returns:
            True если нужно отправить, False иначе
        """
        # ctx.user — объект User
        # ctx.keys — все ключи пользователя
        # ctx.segment_keys — ключи в целевом сегменте

        if not ctx.segment_keys:
            return False

        key = ctx.segment_keys[0]

        # Кастомная логика проверки...
        if key.used_traffic > 0:
            return True

        return False

    async def process(
        self,
        bot: Bot,
        ctx: NotificationContext
    ) -> NotificationResult:
        """
        Отправить сообщение и вернуть результат.

        Args:
            bot: Telegram Bot
            ctx: NotificationContext

        Returns:
            NotificationResult с результатом отправки
        """
        start_time = datetime.now()

        try:
            # Проверить rate limit
            if not await self.rate_limiter.check_limit(ctx.user.tg_id):
                return NotificationResult(
                    user_id=ctx.user.tg_id,
                    funnel_id=self.funnel_id,
                    success=False,
                    message_id=None,
                    error="Rate limit exceeded",
                    sent_at=datetime.now(),
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            # Формировать сообщение
            text = self._format_message(ctx)

            # Отправить сообщение
            message = await bot.send_message(
                chat_id=ctx.user.tg_id,
                text=text,
                parse_mode="HTML"
            )

            # Обновить rate limiter
            await self.rate_limiter.add_sent(ctx.user.tg_id)

            # Дополнительные действия (обновить флаги в БД/кеше)
            await self._mark_sent(ctx)

            return NotificationResult(
                user_id=ctx.user.tg_id,
                funnel_id=self.funnel_id,
                success=True,
                message_id=message.message_id,
                error=None,
                sent_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        except Exception as e:
            return NotificationResult(
                user_id=ctx.user.tg_id,
                funnel_id=self.funnel_id,
                success=False,
                message_id=None,
                error=str(e),
                sent_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def _format_message(self, ctx: NotificationContext) -> str:
        """Форматировать сообщение"""
        key = ctx.segment_keys[0]
        return f"""
🔔 <b>Уведомление</b>

Статус: {key.status}
Трафик: {key.used_traffic} GB
        """.strip()

    async def _mark_sent(self, ctx: NotificationContext) -> None:
        """Отметить что сообщение отправлено"""
        key = ctx.segment_keys[0]
        # Обновить флаг в БД или кеше
        # await self.cache.keys.set(...)
        pass
```

### Пример: KeyExpiryFunnel

```python
# services/notification/funnels/key_expiry.py

from datetime import datetime, timedelta
from models import Key

class KeyExpiryFunnel:
    """Отправляет уведомление о скором истечении ключа (24 часа)"""

    funnel_id = "key_expiry_24h"

    def __init__(self, cache: CacheService, pool: asyncpg.Pool, rate_limiter: RateLimiter):
        self.cache = cache
        self.pool = pool
        self.rate_limiter = rate_limiter

    async def should_send(self, ctx: NotificationContext) -> bool:
        """Проверить истекает ли ключ в 24 часа"""
        if not ctx.segment_keys:
            return False

        key = ctx.segment_keys[0]

        # Истекает ли через 24 часа?
        expires_at = datetime.fromtimestamp(key.expire / 1000)
        time_left = expires_at - datetime.now()

        # Проверить что уже не отправляли уведомление
        if key.notified_24h:
            return False

        return timedelta(hours=23) <= time_left <= timedelta(hours=25)

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        """Отправить уведомление и отметить key.notified_24h"""
        start_time = datetime.now()
        key = ctx.segment_keys[0]

        try:
            if not await self.rate_limiter.check_limit(ctx.user.tg_id):
                return NotificationResult(...)

            # Отправить сообщение с inline кнопкой
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            text = f"""
🔴 <b>Ваш ключ истекает через 24 часа!</b>

Email: {key.email}
Истекает: {self._format_expire_time(key)}
            """.strip()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🔄 Продлить ключ",
                    callback_data=f"key_renewal:{key.email}"
                )
            ]])

            message = await bot.send_message(
                ctx.user.tg_id,
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

            # Отметить в БД что уведомление отправлено
            await self.pool.execute(
                "UPDATE keys SET notified_24h = true WHERE email = $1",
                key.email
            )

            # Обновить в кеше
            key.notified_24h = True
            await self.cache.keys.set(f"key_{key.email}", key)

            await self.rate_limiter.add_sent(ctx.user.tg_id)

            return NotificationResult(
                user_id=ctx.user.tg_id,
                funnel_id=self.funnel_id,
                success=True,
                message_id=message.message_id,
                error=None,
                sent_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        except Exception as e:
            return NotificationResult(
                user_id=ctx.user.tg_id,
                funnel_id=self.funnel_id,
                success=False,
                error=str(e),
                sent_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def _format_expire_time(self, key: Key) -> str:
        """Форматировать время истечения"""
        expires_at = datetime.fromtimestamp(key.expire / 1000)
        return expires_at.strftime("%d.%m.%Y %H:%M")
```

---

## Интеграция

### 1. Регистрация воронок в FunnelManager

```python
# services/conteiner/app.py или main.py

from services.notification import FunnelManager, RateLimiter
from services.notification.funnels import (
    KeyExpiryFunnel,
    TrialReminderFunnel,
    ColdLeadFunnel,
    ReferralBonusFunnel
)

async def setup_notification_manager(container, cache_service, pool):
    """Инициализировать notification manager"""

    rate_limiter = RateLimiter(
        global_rate=25,      # 25 сообщений в секунду
        user_delay_ms=1100   # 1.1 секунды между сообщениями одному пользователю
    )

    manager = FunnelManager(
        cache=cache_service,
        pool=pool
    )

    # Регистрировать воронки
    manager.register(KeyExpiryFunnel(cache_service, pool, rate_limiter))
    manager.register(TrialReminderFunnel(cache_service, rate_limiter))
    manager.register(ColdLeadFunnel(cache_service, rate_limiter))
    manager.register(ReferralBonusFunnel(cache_service, rate_limiter))

    # Добавить в контейнер
    container.register(FunnelManager, instance=manager)

    return manager
```

### 2. Запуск цикла уведомлений

```python
# tasks.py или фоновая задача

from services.notification import FunnelManager

async def run_notifications(bot: Bot, manager: FunnelManager):
    """Запустить цикл уведомлений"""
    try:
        report = await manager.run_cycle(bot)

        # Логировать результаты
        logger.info(
            "Notification cycle completed",
            total_sent=report.total_sent,
            total_failed=report.total_failed,
            duration_ms=report.duration_ms
        )

        # Каждая воронка в report.funnels содержит своё FunnelRunReport
        for funnel_report in report.funnels:
            logger.info(
                f"Funnel {funnel_report.funnel_id} completed",
                sent=funnel_report.total_sent,
                failed=funnel_report.total_failed,
                success_rate=f"{funnel_report.success_rate:.1f}%"
            )

    except Exception as e:
        logger.error("Notification cycle failed", exc_info=True)
```

### 3. Handlers для обработки callback_data от уведомлений

**Создать handlers для кнопок в уведомлениях:**

```python
# handlers/notifications.py

from aiogram import Router, types
from aiogram.filters import Filter
from aiogram_dialog import DialogManager, StartMode

router = Router()


# Фильтр для проверки callback_data
class KeyRenewalCallback(Filter):
    async def __call__(self, query: types.CallbackQuery) -> bool:
        return query.data.startswith("key_renewal:")


class ShowGuideCallback(Filter):
    async def __call__(self, query: types.CallbackQuery) -> bool:
        return query.data.startswith("show_guide:")


@router.callback_query(KeyRenewalCallback())
async def handle_key_renewal(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Обработить кнопку 'Продлить ключ' из уведомления"""
    # Извлечь email из callback_data: "key_renewal:user@example.com"
    email = query.data.split(":", 1)[1]

    await query.answer("Открываю форму продления...")

    # Перейти в диалог продления ключа
    await dialog_manager.start(
        PaymentState.tariff_selection,  # стартовое состояние
        mode=StartMode.RESET_STACK,
        data={"email": email, "payment_type": "renew_key"}
    )


@router.callback_query(ShowGuideCallback())
async def handle_show_guide(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Обработить кнопку 'Инструкция' из уведомления"""
    # Извлечь тип инструкции: "show_guide:connection"
    guide_type = query.data.split(":", 1)[1]

    await query.answer("Показываю инструкцию...")

    # Перейти в диалог с инструкциями
    await dialog_manager.start(
        Instruction.choosing_device,  # диалог выбора устройства
        mode=StartMode.RESET_STACK,
        data={"guide_type": guide_type}
    )
```

**Зарегистрировать handlers в router:**

```python
# main.py

from handlers.notifications import router as notification_router

dp = Dispatcher()
dp.include_router(notification_router)
```

### 4. Планирование в BackgroundTaskManager

```python
# main.py или app.py

from services.notification import FunnelManager

async def on_startup():
    """Инициализировать приложение"""
    # ... инициализация кэша, БД, контейнера ...

    manager = await setup_notification_manager(container, cache, pool)

    # Запускать уведомления каждый час
    background_manager = BackgroundTaskManager()
    background_manager.add_task(
        "notification_cycle",
        run_notifications,
        interval=3600,  # каждый час
        kwargs={"bot": bot, "manager": manager}
    )
```

---

## Примеры

### Пример 1: Простая воронка с inline кнопкой

```python
# Отправлять сообщение всем пользователям с активными ключами каждый день

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class DailyActiveKeyFunnel:
    funnel_id = "daily_active_key"

    def __init__(self, cache: CacheService, rate_limiter: RateLimiter):
        self.cache = cache
        self.rate_limiter = rate_limiter

    async def should_send(self, ctx: NotificationContext) -> bool:
        # Проверить что у пользователя есть активные ключи
        return any(not k.is_expired for k in ctx.keys)

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        if not await self.rate_limiter.check_limit(ctx.user.tg_id):
            return NotificationResult(...)

        active_keys = [k for k in ctx.keys if not k.is_expired]

        text = f"""
✅ <b>Вы в сети!</b>

Активных ключей: {len(active_keys)}
        """.strip()

        # Inline кнопка для перехода в профиль
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="👤 Мой профиль",
                callback_data="open_profile"
            )
        ]])

        message = await bot.send_message(
            ctx.user.tg_id,
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await self.rate_limiter.add_sent(ctx.user.tg_id)

        return NotificationResult(
            user_id=ctx.user.tg_id,
            funnel_id=self.funnel_id,
            success=True,
            message_id=message.message_id,
            error=None,
            sent_at=datetime.now(),
            duration_ms=0
        )
```

**Handler для кнопки:**

```python
# handlers/notifications.py

@router.callback_query(F.data == "open_profile")
async def handle_open_profile(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Открыть профиль пользователя"""
    await query.answer("Открываю профиль...")

    await dialog_manager.start(
        KeysInit.waiting_for_action,
        mode=StartMode.RESET_STACK
    )
```

### Пример 2: Воронка с условной логикой

```python
# Отправлять сообщение если пользователь не использовал ключ 7 дней

class UnusedKeyReminderFunnel:
    funnel_id = "unused_7d"

    def __init__(self, cache: CacheService, pool: asyncpg.Pool, rate_limiter: RateLimiter):
        self.cache = cache
        self.pool = pool
        self.rate_limiter = rate_limiter

    async def should_send(self, ctx: NotificationContext) -> bool:
        if not ctx.segment_keys:
            return False

        key = ctx.segment_keys[0]

        # Ключ есть, активен, но не использован более 7 дней
        if key.is_expired or key.used_traffic > 0:
            return False

        # Проверить last_used дату
        last_used = await self._get_last_used(key.email)
        if not last_used:
            return False

        days_unused = (datetime.now() - last_used).days
        return days_unused >= 7 and not key.notified_7d

    async def process(self, bot: Bot, ctx: NotificationContext) -> NotificationResult:
        if not await self.rate_limiter.check_limit(ctx.user.tg_id):
            return NotificationResult(...)

        key = ctx.segment_keys[0]

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        text = f"""
⚠️ <b>Ваш ключ не используется</b>

Вы не подключались {self._get_days_unused(key.email)} дней.
        """.strip()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📖 Инструкция",
                callback_data=f"show_guide:connection"
            )
        ]])

        message = await bot.send_message(
            ctx.user.tg_id,
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Отметить уведомление
        key.notified_7d = True
        await self.cache.keys.set(f"key_{key.email}", key)

        await self.rate_limiter.add_sent(ctx.user.tg_id)

        return NotificationResult(
            user_id=ctx.user.tg_id,
            funnel_id=self.funnel_id,
            success=True,
            message_id=message.message_id,
            error=None,
            sent_at=datetime.now(),
            duration_ms=0
        )

    async def _get_last_used(self, email: str) -> Optional[datetime]:
        """Получить дату последнего использования"""
        # SELECT last_used FROM keys WHERE email = $1
        pass

    def _get_days_unused(self, email: str) -> int:
        """Получить количество дней неиспользования"""
        # Вычислить из last_used
        pass
```

**Handlers для кнопок:**

```python
# handlers/notifications.py

@router.callback_query(F.data.startswith("show_guide:"))
async def handle_show_guide(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Открыть инструкцию"""
    guide_type = query.data.split(":", 1)[1]
    await query.answer()

    await dialog_manager.start(
        Instruction.choosing_device,
        mode=StartMode.RESET_STACK,
        data={"guide_type": guide_type}
    )
```

---

## Настройка

### SENDING_HOUR_WINDOW

**Управление временем отправки сообщений**

```python
# services/notification/routing.py

SENDING_HOUR_WINDOW = (9, 23)  # Отправлять только между 9 и 23 часами
```

Проверка в FunnelManager:

```python
from datetime import datetime
from services.notification.routing import SENDING_HOUR_WINDOW

async def run_cycle(self, bot: Bot) -> FunnelRunReport:
    current_hour = datetime.now().hour

    if not (SENDING_HOUR_WINDOW[0] <= current_hour < SENDING_HOUR_WINDOW[1]):
        logger.info(f"Outside sending window (current: {current_hour}h)")
        return FunnelRunReport(...)  # Пустой отчёт

    # Продолжить отправку уведомлений...
```

### RateLimiter настройка

```python
from services.notification import RateLimiter

# Глобальный лимит 25 msg/s, персональный 1.1s между сообщениями
rate_limiter = RateLimiter(
    global_rate=25,      # Максимум 25 сообщений в секунду
    user_delay_ms=1100   # Минимум 1.1 секунды между сообщениями одному пользователю
)
```

---

## Тестирование

### Тестирование воронки

```python
# tests/services/notification/test_my_funnel.py

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from models import User, Key
from services.notification.models import NotificationContext, NotificationResult
from services.notification.funnels.my_funnel import MyFunnel


@pytest.fixture
def my_funnel():
    cache = AsyncMock()
    rate_limiter = AsyncMock()
    return MyFunnel(cache, rate_limiter)


@pytest.mark.asyncio
async def test_should_send_true(my_funnel):
    """Тест should_send когда нужно отправить"""
    user = User(tg_id=123, username="test")
    key = Key(email="test@example.com", used_traffic=10)

    ctx = NotificationContext(
        user=user,
        keys=[key],
        segment_keys=[key],
        funnel_id="my_funnel",
        timestamp=datetime.now()
    )

    result = await my_funnel.should_send(ctx)
    assert result is True


@pytest.mark.asyncio
async def test_should_send_false_no_keys(my_funnel):
    """Тест should_send когда нет ключей"""
    user = User(tg_id=123, username="test")

    ctx = NotificationContext(
        user=user,
        keys=[],
        segment_keys=[],
        funnel_id="my_funnel",
        timestamp=datetime.now()
    )

    result = await my_funnel.should_send(ctx)
    assert result is False


@pytest.mark.asyncio
async def test_process_success(my_funnel):
    """Тест успешной отправки"""
    bot = AsyncMock()
    user = User(tg_id=123, username="test")
    key = Key(email="test@example.com", used_traffic=10)

    ctx = NotificationContext(
        user=user,
        keys=[key],
        segment_keys=[key],
        funnel_id="my_funnel",
        timestamp=datetime.now()
    )

    # Настроить моки
    my_funnel.rate_limiter.check_limit = AsyncMock(return_value=True)
    my_funnel.rate_limiter.add_sent = AsyncMock()
    bot.send_message = AsyncMock(return_value=AsyncMock(message_id=42))

    result = await my_funnel.process(bot, ctx)

    assert result.success is True
    assert result.message_id == 42
    bot.send_message.assert_called_once()
    my_funnel.rate_limiter.add_sent.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_process_rate_limit_exceeded(my_funnel):
    """Тест когда превышен rate limit"""
    bot = AsyncMock()
    user = User(tg_id=123, username="test")
    key = Key(email="test@example.com", used_traffic=10)

    ctx = NotificationContext(
        user=user,
        keys=[key],
        segment_keys=[key],
        funnel_id="my_funnel",
        timestamp=datetime.now()
    )

    my_funnel.rate_limiter.check_limit = AsyncMock(return_value=False)

    result = await my_funnel.process(bot, ctx)

    assert result.success is False
    assert "Rate limit" in result.error
    bot.send_message.assert_not_called()
```

### Интеграционный тест

```python
# tests/services/notification/test_manager.py

@pytest.mark.asyncio
async def test_run_cycle(cache_service, pool):
    """Тест полного цикла уведомлений"""
    bot = AsyncMock()
    rate_limiter = AsyncMock()
    rate_limiter.check_limit = AsyncMock(return_value=True)

    funnel = MyFunnel(cache_service, rate_limiter)

    manager = FunnelManager(cache=cache_service, pool=pool)
    manager.register(funnel)

    # Загрузить тестовых пользователей в кеш
    user = User(tg_id=123, username="test")
    key = Key(email="test@example.com", used_traffic=10)

    await cache_service.users.set("user_123", user)
    await cache_service.keys.set("key_test@example.com", key)

    # Запустить цикл
    report = await manager.run_cycle(bot)

    # Проверить отчёт
    assert report.total_sent >= 0
    assert len(report.funnels) == 1

    funnel_report = report.funnels[0]
    assert funnel_report.funnel_id == "my_funnel"
```

---

## FAQ

### В: Как добавить новую воронку?

**О:**
1. Создать класс в `services/notification/funnels/` с наследованием `NotificationFunnelProtocol`
2. Реализовать `should_send()` и `process()`
3. Зарегистрировать в `FunnelManager`

### В: Как исключить пользователя из воронки?

**О:** В методе `should_send()` вернуть `False`:

```python
async def should_send(self, ctx: NotificationContext) -> bool:
    # Исключить пользователей с ID в чёрном списке
    if ctx.user.tg_id in BLACKLIST_USERS:
        return False
    return True
```

### В: Как изменить время отправки?

**О:** Обновить `SENDING_HOUR_WINDOW` в `routing.py`:

```python
SENDING_HOUR_WINDOW = (10, 22)  # 10:00 - 22:00
```

### В: Как отключить rate limiting?

**О:** Не рекомендуется, но можно:

```python
rate_limiter = RateLimiter(
    global_rate=999999,  # Очень высокий лимит
    user_delay_ms=0      # Без задержки
)
```

### В: Как просмотреть результаты последнего цикла?

**О:**

```python
report = await manager.run_cycle(bot)

for funnel_report in report.funnels:
    logger.info(f"Funnel: {funnel_report.funnel_id}")
    logger.info(f"  Sent: {funnel_report.total_sent}")
    logger.info(f"  Failed: {funnel_report.total_failed}")
    logger.info(f"  Success rate: {funnel_report.success_rate:.1f}%")

    for result in funnel_report.results:
        if not result.success:
            logger.warning(f"  Failed for user {result.user_id}: {result.error}")
```

---

**Версия:** 1.0 (2026-03-04)
**Последнее обновление:** 2026-03-04
**Статус:** ✅ Документация завершена
