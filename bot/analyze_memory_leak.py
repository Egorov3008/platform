#!/usr/bin/env python3
"""
Скрипт для анализа утечки памяти в боте.
Запускать через: python3 analyze_memory_leak.py
"""

import asyncio
import gc
import sys
import tracemalloc
import linecache
from collections import defaultdict
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, '/home/tds_admin/Bot_3xui_vpn')


def get_objects_by_type():
    """Получить количество объектов по типам"""
    objects = defaultdict(int)
    for obj in gc.get_objects():
        try:
            type_name = type(obj).__name__
            objects[type_name] += 1
        except:
            pass
    return dict(sorted(objects.items(), key=lambda x: x[1], reverse=True)[:30])


def analyze_garbage():
    """Анализ сборщика мусора"""
    gc.collect()
    
    print("\n=== Сборщик мусора ===")
    print(f"Поколение 0: {gc.count()[0]} объектов")
    print(f"Поколение 1: {gc.count()[1]} объектов")
    print(f"Поколение 2: {gc.count()[2]} объектов")
    print(f"Порог поколения 0: {gc.get_threshold()[0]}")
    print(f"Порог поколения 1: {gc.get_threshold()[1]}")
    print(f"Порог поколения 2: {gc.get_threshold()[2]}")


def analyze_memory_trend():
    """Анализ тренда потребления памяти"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    print("\n=== Потребление памяти процессом ===")
    mem_info = process.memory_info()
    print(f"RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
    print(f"Memory %: {process.memory_percent():.2f}%")
    
    # Информация о системе
    system_memory = psutil.virtual_memory()
    print(f"\n=== Системная память ===")
    print(f"Total: {system_memory.total / 1024 / 1024 / 1024:.2f} GB")
    print(f"Available: {system_memory.available / 1024 / 1024:.2f} MB")
    print(f"Used: {system_memory.percent:.2f}%")
    print(f"Swap Used: {psutil.swap_memory().percent:.2f}%")


async def monitor_memory_snapshots(interval=5, count=3):
    """
    Сделать несколько снимков памяти для выявления утечек.
    Сравнивает распределение памяти между снимками.
    """
    from services.container.app import get_container
    from services.cache.service import CacheService
    
    print("\n=== Мониторинг утечек памяти ===")
    print(f"Сделаем {count} снимков с интервалом {interval} сек...")
    
    tracemalloc.start()
    
    snapshots = []
    for i in range(count):
        await asyncio.sleep(interval)
        
        # Принудительная сборка мусора перед снимком
        gc.collect()
        
        snapshot = tracemalloc.take_snapshot()
        snapshots.append(snapshot)
        
        top_stats = snapshot.statistics('lineno')
        print(f"\n--- Снимок {i+1} ---")
        print(f"Топ-5 по памяти:")
        for index, stat in enumerate(top_stats[:5], 1):
            print(f"{index}. {stat.size / 1024:.1f} KB: {stat.traceback}")
    
    # Сравнение первого и последнего снимка
    if len(snapshots) >= 2:
        print("\n=== Сравнение снимков ===")
        first_stats = snapshots[0].statistics('lineno')
        last_stats = snapshots[-1].statistics('lineno')
        
        print("\nУвеличение потребления (топ-10):")
        for stat in last_stats[:10]:
            size_kb = stat.size / 1024
            print(f"  {size_kb:.1f} KB: {stat.traceback}")
    
    tracemalloc.stop()


async def analyze_cache_memory():
    """Анализ потребления памяти кешем"""
    from services.container.app import get_container
    from services.cache.service import CacheService
    
    print("\n=== Анализ кеша ===")
    
    try:
        container = await get_container()
        cache_service: CacheService = container.resolve(CacheService)
        
        # Получаем статистику по моделям в кеше
        models = {
            'users': cache_service.users,
            'keys': cache_service.keys,
            'servers': cache_service.servers,
            'tariffs': cache_service.tariffs,
            'gifts': cache_service.gifts,
            'inbounds': cache_service.inbounds,
            'payments': cache_service.payments,
        }
        
        total_objects = 0
        print("\nОбъектов в кеше по моделям:")
        for name, model_cache in models.items():
            count = len(await model_cache.all())
            total_objects += count
            print(f"  {name}: {count} объектов")
        
        print(f"\nВсего объектов в кеше: {total_objects}")
        
    except Exception as e:
        print(f"Ошибка анализа кеша: {e}")


async def analyze_async_objects():
    """Анализ асинхронных задач и соединений"""
    print("\n=== Асинхронные объекты ===")
    
    # Активные задачи
    tasks = asyncio.all_tasks()
    print(f"Активных задач: {len(tasks)}")
    for task in list(tasks)[:10]:
        print(f"  - {task.get_name()}: {task}")
    
    # Проверка на зомби-объекты
    gc.collect()
    unclosed = [obj for obj in gc.get_objects() 
                if type(obj).__name__ in ('ClientSession', 'Connection', 'Pool')]
    if unclosed:
        print(f"\n⚠️ Найдено {len(unclosed)} потенциально не закрытых объектов:")
        for obj in unclosed[:5]:
            print(f"  - {type(obj).__name__}")


async def main():
    print("=" * 60)
    print("АНАЛИЗ УТЕЧКИ ПАМЯТИ")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Общая информация
    analyze_memory_trend()
    
    # 2. Сборщик мусора
    analyze_garbage()
    
    # 3. Топ объектов
    print("\n=== Топ объектов по типам ===")
    objects = get_objects_by_type()
    for type_name, count in list(objects.items())[:15]:
        print(f"  {type_name}: {count}")
    
    # 4. Асинхронные объекты
    await analyze_async_objects()
    
    # 5. Кеш
    await analyze_cache_memory()
    
    # 6. Мониторинг тренда
    await monitor_memory_snapshots(interval=3, count=3)
    
    print("\n" + "=" * 60)
    print("АНАЛИЗ ЗАВЕРШЕН")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nАнализ прерван пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()
