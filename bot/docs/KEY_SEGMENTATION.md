# Сегментация ключей

Модуль сегментации ключей предоставляет удобный способ классификации и фильтрации VPN ключей по различным критериям.

## Сегменты ключей

### `KeySegment` enum

Доступные сегменты:

- **EXPIRING_24H** — Ключи, истекающие в ближайшие 24 часа
- **EXPIRING_7D** — Ключи, истекающие в ближайшие 7 дней
- **EXPIRING_30D** — Ключи, истекающие в ближайшие 30 дней
- **EXPIRED** — Истёкшие ключи
- **ACTIVE** — Активные платные ключи (не истекли и не trial)
- **TRIAL** — Trial ключи (tariff_id == 10)
- **UNUSED** — Неиспользуемые ключи (total_gb == 0)
- **ALL** — Все ключи

## Использование

### 1. Прямое использование `KeySegmenter`

```python
from services.core.segmentation import KeySegmenter
from models import Key

# Создать сегментатор
segmenter = KeySegmenter()

# Определить сегмент для ключа
segment = await segmenter.determine_segment(key)

# Отфильтровать ключи по сегменту
expiring_keys = await segmenter.filter_keys(all_keys, KeySegment.EXPIRING_24H)
```

### 2. Использование `KeySegmentationService`

Рекомендуемый способ для использования в сервисах:

```python
from services.core.keys.segmentation import KeySegmentationService

# Создать сервис
service = KeySegmentationService()

# Распределить ключи по всем сегментам
distribution = await service.segment_keys(all_keys)

# Получить ключи по конкретному критерию
expiring_24h = await service.get_expiring_24h(all_keys)
expired = await service.get_expired(all_keys)
active = await service.get_active(all_keys)
trial = await service.get_trial(all_keys)
unused = await service.get_unused(all_keys)

# Получить статистику по сегментам
stats = service.get_segment_stats()
print(f"Expiring в 24h: {stats.get('expiring_24h', 0)}")
```

### 3. Использование в DI контейнере

```python
from services.core.keys.segmentation import KeySegmentationService

# Регистрация в контейнере
container.register(KeySegmentationService, scope=punq.Scope.singleton)

# Использование в сервисе
class MyService:
    def __init__(self, segmentation_service: KeySegmentationService):
        self.segmentation = segmentation_service

    async def process_keys(self, keys):
        expiring = await self.segmentation.get_expiring_24h(keys)
        # Обработать ключи, истекающие в 24 часа
```

## Примеры

### Пример 1: Отправить уведомления об истекающих ключах

```python
async def notify_expiring_keys():
    cache = dialog_manager.middleware_data.get("cache")
    segmentation = KeySegmentationService()

    # Получить все ключи
    all_keys = await cache.keys.all()

    # Получить ключи, истекающие в 24 часа
    expiring = await segmentation.get_expiring_24h(all_keys)

    for key in expiring:
        user = await cache.users.get(f"user_{key.tg_id}")
        await send_notification(user, key, "Your key is expiring in 24 hours!")
```

### Пример 2: Получить статистику

```python
async def get_key_statistics(cache):
    segmentation = KeySegmentationService()

    all_keys = await cache.keys.all()
    distribution = await segmentation.segment_keys(all_keys)

    stats = {
        "total": len(all_keys),
        "expiring_24h": len(distribution.get(KeySegment.EXPIRING_24H, [])),
        "expired": len(distribution.get(KeySegment.EXPIRED, [])),
        "active": len(distribution.get(KeySegment.ACTIVE, [])),
        "trial": len(distribution.get(KeySegment.TRIAL, [])),
        "unused": len(distribution.get(KeySegment.UNUSED, [])),
    }

    return stats
```

### Пример 3: Использование в команде администратора

```python
async def on_click_key_report(callback, button, dialog_manager):
    cache = dialog_manager.middleware_data.get("cache")
    segmentation = KeySegmentationService()

    all_keys = await cache.keys.all()
    distribution = await segmentation.segment_keys(all_keys)

    message = "📊 **Отчёт по ключам:**\n\n"
    for segment, keys in distribution.items():
        message += f"• {segment.value}: {len(keys)}\n"

    await callback.answer(message, show_alert=True)
```

## Архитектура

### `KeyCondition` - базовый класс условий

Условия проверяют, принадлежит ли ключ определённому сегменту:

```python
class KeyCondition(BaseCondition):
    async def check_key(self, key: Key) -> bool:
        # Проверить условие
        pass
```

### `KeySegmenter` - определитель сегментов

Использует условия для определения сегмента каждого ключа:

```python
segmenter = KeySegmenter()
segment = await segmenter.determine_segment(key)
```

Результаты кешируются на 5 минут.

### `KeySegmentationManager` - менеджер распределения

Распределяет коллекцию ключей по сегментам:

```python
manager = KeySegmentationManager(segmenter)
distribution = await manager.distribution_process(keys)
```

### `KeySegmentationService` - сервис

Высокоуровневый API для работы с сегментацией ключей.

## Тестирование

Модуль включает полный набор тестов:

```bash
pytest tests/services/core/segmentation/test_key_segmenter.py -v
```

## Производительность

- **Кеширование:** Результаты кешируются на 5 минут
- **Фильтрация:** O(n) временная сложность для фильтрации n ключей
- **Память:** O(n) для хранения распределения по сегментам

## Примечания

1. **Порядок проверки правил:** Более специфичные условия проверяются раньше (истекший → trial → unused → expiring_* → active)
2. **Взаимоисключаемость:** Каждый ключ может принадлежать только одному сегменту
3. **Fallback:** Если ключ не подходит ни под одно условие, он помещается в сегмент ALL
