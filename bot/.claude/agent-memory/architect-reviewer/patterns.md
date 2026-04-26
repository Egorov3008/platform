# Паттерны и anti-patterns — Bot 3xui

## `_name` в dataclass-моделях — системная проблема

### Корень проблемы

`dataclasses.asdict()` включает **все instance fields**, включая поля с `_`-префиксом.
`ClassVar`-поля (без аннотации типа или с `ClassVar[T]`) — НЕ включаются.

Разница:
```python
# INSTANCE FIELD — включается asdict():
_name: str = "payment"          # аннотирован → dataclass field

# CLASS VAR — НЕ включается asdict():
_name = "payment"               # без аннотации → class variable (Inbound)
_name: ClassVar[str] = "payment"  # ClassVar → тоже class variable
```

### Статус по моделям

| Файл | Тип `_name` | Сломан? |
|------|------------|---------|
| `models/payments/payment.py:17` | `_name: str = "payment"` | ДА |
| `models/users/user.py:28` | `_name = "user"` (без аннотации!) | НЕТ — ClassVar |
| `models/tariffs/tariff.py:13` | `_name: str = "tariff"` | ДА |
| `models/servers/server.py:13` | `_name: str = "servers"` | ДА |
| `models/gifts/gift_link.py:17,18` | `_name: str` + `_status: str` | ДА (2 поля) |
| `models/stocks/stock.py:20` | `_name: Optional[str] = "stock"` | ДА |
| `models/keys/key.py:30` | `_name: str = "key"` | НЕТ — фильтрует `_DB_FIELDS` |
| `models/servers/inbound.py:9` | `_name = "inbound"` (без аннотации) | НЕТ — ClassVar |

### Почему `User` и `Inbound` не сломаны

`User._name = "user"` и `Inbound._name = "inbound"` — без аннотации типа.
Python dataclass НЕ регистрирует их как поля, они остаются class variables.
`asdict()` их не включает. Но это хрупко — добавление аннотации сломает их.

### Правильное исправление

**В каждой сломанной модели** заменить:
```python
_name: str = "payment"
```
на:
```python
from typing import ClassVar
_name: ClassVar[str] = "payment"
```

Альтернатива — whitelist как в `Key._DB_FIELDS`:
```python
_DB_FIELDS = frozenset({'payment_id', 'tg_id', 'amount', ...})
def to_dict(self):
    return {k: v for k, v in asdict(self).items() if k in self._DB_FIELDS}
```

### Почему НЕ фиксить в `BaseRepository.create()`

`database/base.py` — слой репозитория (инфраструктура).
Фильтрация служебных полей модели — ответственность модели, не БД-слоя.
Добавление фильтра `if not k.startswith('_')` в create() создаст "магическое" поведение
и скроет следующую аналогичную ошибку в других сценариях (update, delete).

### Побочная проблема: `delete_data()` тоже уязвим

`BaseData.delete_data()` (base.py:152): `self.service.delete(conn, **data.to_dict())`
`BaseRepository.delete()` берёт только первый ключ из kwargs через `next(iter(...))`.
Порядок ключей в dict зависит от порядка полей в dataclass.
Если `_name` идёт первым → `DELETE FROM t WHERE _name = $1` → неверный запрос.
(На практике `_name` обычно последнее поле — риск низкий, но архитектурно некорректно.)

---

## Legacy-функции в getters/on_click/admin_click.py (ревью 2026-03-04)

| Функция | Статус | Ссылки |
|---------|--------|--------|
| `on_click_24h_keys` | ДУБЛИКАТ | Заменена `admin_keys.py` |
| `on_click_expired_keys` | ДУБЛИКАТ | Заменена `admin_keys.py` |
| `on_click_all_keys` | ДУБЛИКАТ | Заменена `admin_keys.py` |
| `on_click_date_selection` | МЁРТВАЯ | Нигде не вызывается |
| `on_click_view_tariff_admin` | МЁРТВАЯ | Нигде не вызывается |
| `on_click_confirmation_tariff_email` | МЁРТВАЯ | Нигде не вызывается |
| `on_clik_process_key_edit` | ПОЧТИ МЁРТВАЯ | Только `widgets/keybord.py` |
| `on_click_done_registrate` | МЁРТВАЯ + TYPE ERROR | cache: CacheMiddleware не CacheService |

`click_sync_cache` (строка 344) — АКТИВНА (вызывается из `panel.py`), но содержит
`PanelDataSync` без импорта → NameError в runtime при нажатии кнопки синхронизации.

## TypeError в GiftActivationScenario._process_success() (2026-03-04)

`services/scenarios/gift_scenario.py:106`:
`await self.cache.gifts.temporary_set(CacheKeyManager.gift_activation(user_id), **data)`
Сигнатура: `temporary_set(key, ttl: timedelta, **kwargs)` — `ttl` обязателен, позиционный.
Вызов передаёт только `**data` (нет `ttl`) → TypeError при любой активации подарка.

## Cross-layer coupling: core/segmentation → notification/core

`services/core/segmentation/manager.py:3`: `from services.notification.core import UserSegmenter`
Дубликат в `services/core/segmentation/ruls.py:79` (более актуальная версия).
Исправление: в `manager.py` заменить импорт на `from .ruls import UserSegmenter`.

## AdminUserManagement.profile_user — состояние-призрак (2026-03-04)

Используется в `key_click.py:68` как цель после удаления ключа в admin-контексте,
но отсутствует в `dialogs/windows/__init__.py:ALL_WINDOW_CONFIGS`.
При нажатии "Удалить ключ" из admin-контекста → aiogram-dialog не найдёт стейт.

## partner_dialog.py — двойная проблема (2026-03-04)

1. `from state import PartnerProgram` — модуля `state.py` нет, только пакет `states/` → ImportError
2. `partner_static_win` нигде не используется
