# Быстрый старт: Сегментация ключей

## Основные функции

Модуль сегментации ключей автоматически классифицирует ключи по состоянию:

```
├── EXPIRING_24H    — истекают в ближайшие 24 часа  ⏰
├── EXPIRING_7D     — истекают в 7 дней            📅
├── EXPIRING_30D    — истекают в 30 дней           📆
├── EXPIRED         — уже истекшие                  🔴
├── ACTIVE          — активные платные             ✅
├── TRIAL           — пробные ключи                🎯
├── UNUSED          — неиспользуемые (0 Гб)        📵
└── ALL             — все остальные                🔹
```

## Использование в коде

### 1️⃣ Получить ключи определённого сегмента

```python
from services.core.keys.segmentation import KeySegmentationService

service = KeySegmentationService()

# Ключи, истекающие в 24 часа
expiring = await service.get_expiring_24h(all_keys)

# Истёкшие ключи
expired = await service.get_expired(all_keys)

# Активные ключи
active = await service.get_active(all_keys)

# Пробные ключи
trial = await service.get_trial(all_keys)

# Неиспользуемые ключи
unused = await service.get_unused(all_keys)
```

### 2️⃣ Распределить все ключи по сегментам

```python
# Распределить все ключи
distribution = await service.segment_keys(all_keys)

# distribution = {
#     KeySegment.EXPIRING_24H: [key1, key2, ...],
#     KeySegment.EXPIRED: [key3, ...],
#     KeySegment.ACTIVE: [key4, key5, ...],
#     ...
# }

for segment, keys in distribution.items():
    print(f"{segment.value}: {len(keys)} ключей")
```

### 3️⃣ Получить статистику

```python
stats = service.get_segment_stats()

print(f"Всего: {stats['total']}")
print(f"Истекают в 24ч: {stats['expiring_24h']}")
print(f"Истёкших: {stats['expired']}")
print(f"Активных: {stats['active']}")
```

### 4️⃣ Использование в DI контейнере

```python
from services.core.keys.segmentation import KeySegmentationService

class MyAdminService:
    def __init__(self, segmentation: KeySegmentationService):
        self.segmentation = segmentation

    async def send_expiry_notifications(self, cache):
        keys = await cache.keys.all()
        expiring = await self.segmentation.get_expiring_24h(keys)

        for key in expiring:
            await self.notify_user(key.tg_id)
```

## Использование в админ-панели

### Пример: Отчёт по ключам

```python
from services.core.keys.admin_report import KeyAdminReport

report = KeyAdminReport()

# Получить текстовый отчёт
message = await report.format_report_text(all_keys)
# 📊 Отчёт по ключам
#
# Всего ключей: 150
# Активных: 120
# ...

# Получить детали по истекающим
details = await report.get_expiring_24h_details(all_keys)

# Получить детали по истёкшим
expired_details = await report.get_expired_details(all_keys)
```

## Примеры использования

### Пример 1: Отправить уведомления

```python
async def notify_expiring_keys(dialog_manager: DialogManager):
    cache = dialog_manager.middleware_data.get("cache")
    service = KeySegmentationService()

    all_keys = await cache.keys.all()
    expiring = await service.get_expiring_24h(all_keys)

    for key in expiring:
        await send_notification(
            f"Your key {key.email} is expiring in 24 hours!",
            user_id=key.tg_id
        )
```

### Пример 2: Удалить истёкшие ключи

```python
async def cleanup_expired_keys(cache):
    service = KeySegmentationService()

    all_keys = await cache.keys.all()
    expired = await service.get_expired(all_keys)

    for key in expired:
        await delete_key(key.email)
        await cache.keys.delete(key.email)
```

### Пример 3: Генератор отчётов в админке

```python
class AdminReportGetter:
    def __init__(self):
        self.report = KeyAdminReport()

    async def get_key_report(self, dialog_manager, **kwargs):
        cache = dialog_manager.middleware_data.get("cache")
        all_keys = await cache.keys.all()

        return {
            "report": await self.report.format_report_text(all_keys),
            "stats": await self.report.get_summary_stats(all_keys),
        }
```

## Тестирование

Запустить тесты:

```bash
# Все тесты сегментации
pytest tests/services/core/segmentation/ -v

# Только тесты ключей
pytest tests/services/core/segmentation/test_key_segmenter.py -v

# С покрытием
pytest tests/services/core/segmentation/ --cov
```

## Производительность

- **Скорость:** O(n) для распределения n ключей
- **Кеширование:** 5 минут на результат за ключ
- **Память:** O(n) для хранения распределения

## Документация

Полная документация: [`docs/KEY_SEGMENTATION.md`](docs/KEY_SEGMENTATION.md)

## Файлы

```
services/core/segmentation/
├── key_model.py          # KeySegment enum
├── key_ruls.py           # KeyCondition + KeySegmenter
└── key_manager.py        # KeySegmentationManager

services/core/keys/
├── segmentation.py       # KeySegmentationService
└── admin_report.py       # KeyAdminReport

dialogs/windows/getters/admin/
└── key_segmentation_report.py  # Геттер для диалогов
```
