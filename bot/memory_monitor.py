#!/usr/bin/env python3
"""
Скрипт для непрерывного мониторинга памяти бота.
Записывает статистику в CSV файл для последующего анализа.
"""

import asyncio
import csv
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/tds_admin/Bot_3xui_vpn')

import psutil

LOG_FILE = Path('/home/tds_admin/Bot_3xui_vpn/memory_monitor.csv')
INTERVAL = 10  # секунд между замерами


def get_bot_process():
    """Найти процесс бота"""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'python3' in cmdline and 'main.py' in cmdline:
                return psutil.Process(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def get_memory_stats(process: psutil.Process):
    """Получить статистику памяти"""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'pid': process.pid if process else None,
    }
    
    if process:
        try:
            mem_info = process.memory_info()
            stats['bot_rss_mb'] = round(mem_info.rss / 1024 / 1024, 2)
            stats['bot_vms_mb'] = round(mem_info.vms / 1024 / 1024, 2)
            stats['bot_memory_percent'] = round(process.memory_percent(), 2)
            
            # Информация о потоках
            stats['bot_threads'] = process.num_threads()
            stats['bot_connections'] = process.num_fds() if hasattr(process, 'num_fds') else 'N/A'
        except psutil.NoSuchProcess:
            stats['bot_rss_mb'] = 'DEAD'
            stats['bot_vms_mb'] = 'DEAD'
            stats['bot_memory_percent'] = 'DEAD'
    else:
        stats['bot_rss_mb'] = 'NOT_FOUND'
        stats['bot_vms_mb'] = 'NOT_FOUND'
        stats['bot_memory_percent'] = 'NOT_FOUND'
    
    # Системная память
    system_memory = psutil.virtual_memory()
    stats['system_total_gb'] = round(system_memory.total / 1024 / 1024 / 1024, 2)
    stats['system_available_mb'] = round(system_memory.available / 1024 / 1024, 2)
    stats['system_percent'] = round(system_memory.percent, 2)
    
    # Swap
    swap = psutil.swap_memory()
    stats['swap_percent'] = round(swap.percent, 2)
    stats['swap_used_mb'] = round(swap.used / 1024 / 1024, 2)
    
    return stats


def init_csv():
    """Инициализировать CSV файл"""
    fieldnames = [
        'timestamp', 'pid', 'bot_rss_mb', 'bot_vms_mb', 'bot_memory_percent',
        'bot_threads', 'bot_connections', 'system_total_gb', 
        'system_available_mb', 'system_percent', 'swap_percent', 'swap_used_mb'
    ]
    
    file_exists = LOG_FILE.exists()
    
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
    
    return fieldnames


async def monitor():
    """Основной цикл мониторинга"""
    running = True
    
    def signal_handler(sig, frame):
        nonlocal running
        print("\nОстановка мониторинга...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 70)
    print("МОНИТОРИНГ ПАМЯТИ БОТА")
    print(f"Интервал: {INTERVAL} сек")
    print(f"Лог файл: {LOG_FILE}")
    print("=" * 70)
    print(f"{'Время':<20} {'PID':<8} {'RSS MB':<10} {'% Mem':<8} {'Sys Avail':<12} {'Swap%':<8}")
    print("-" * 70)
    
    init_csv()
    
    while running:
        try:
            process = get_bot_process()
            stats = get_memory_stats(process)
            
            # Вывод в консоль
            pid_str = str(stats['pid']) if stats['pid'] else 'N/A'
            rss_str = str(stats['bot_rss_mb']) if isinstance(stats['bot_rss_mb'], (int, float)) else stats['bot_rss_mb']
            mem_str = str(stats['bot_memory_percent']) if isinstance(stats['bot_memory_percent'], (int, float)) else stats['bot_memory_percent']
            avail_str = f"{stats['system_available_mb']} MB"
            swap_str = f"{stats['swap_percent']}%"
            
            print(f"{stats['timestamp'][11:19]:<20} {pid_str:<8} {rss_str:<10} {mem_str:<8} {avail_str:<12} {swap_str:<8}")
            
            # Запись в CSV
            with open(LOG_FILE, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=init_csv())
                writer.writerow(stats)
            
            # Проверка на проблемы
            if isinstance(stats['bot_memory_percent'], (int, float)):
                if stats['bot_memory_percent'] > 50:
                    print(f"  ⚠️  WARNING: Бот использует {stats['bot_memory_percent']}% памяти!")
                if stats['system_percent'] > 85:
                    print(f"  ⚠️  WARNING: Система использует {stats['system_percent']}% памяти!")
                if stats['swap_percent'] > 50:
                    print(f"  ⚠️  WARNING: Swap использован на {stats['swap_percent']}%!")
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        await asyncio.sleep(INTERVAL)
    
    print("\nМониторинг завершен")


def analyze_csv():
    """Анализ CSV файла"""
    if not LOG_FILE.exists():
        print(f"Файл {LOG_FILE} не найден")
        return
    
    import pandas as pd
    
    df = pd.read_csv(LOG_FILE)
    
    print("\n" + "=" * 70)
    print("АНАЛИЗ НАКОПЛЕННЫХ ДАННЫХ")
    print("=" * 70)
    
    if 'bot_rss_mb' in df.columns:
        # Преобразуем в числа, отфильтровав строки
        df['bot_rss_mb'] = pd.to_numeric(df['bot_rss_mb'], errors='coerce')
        df['bot_memory_percent'] = pd.to_numeric(df['bot_memory_percent'], errors='coerce')
        df['system_percent'] = pd.to_numeric(df['system_percent'], errors='coerce')
        
        print(f"\nЗаписей: {len(df)}")
        print(f"Период: {df['timestamp'].iloc[0]} — {df['timestamp'].iloc[-1]}")
        
        print("\n📊 Статистика памяти бота (RSS MB):")
        print(f"  Min: {df['bot_rss_mb'].min():.2f}")
        print(f"  Max: {df['bot_rss_mb'].max():.2f}")
        print(f"  Avg: {df['bot_rss_mb'].mean():.2f}")
        print(f"  Std: {df['bot_rss_mb'].std():.2f}")
        
        # Тренд
        if len(df) > 10:
            first_avg = df['bot_rss_mb'].iloc[:10].mean()
            last_avg = df['bot_rss_mb'].iloc[-10:].mean()
            trend = last_avg - first_avg
            trend_percent = (trend / first_avg * 100) if first_avg > 0 else 0
            print(f"\n📈 Тренд: {trend:+.2f} MB ({trend_percent:+.1f}%)")
            
            if trend > 50:
                print("  ⚠️  ОБНАРУЖЕН РОСТ ПАМЯТИ - возможна утечка!")
            elif trend < -50:
                print("  ✓ Память уменьшается - возможна сборка мусора")
            else:
                print("  ✓ Память стабильна")
        
        print("\n📊 Системная память (%):")
        print(f"  Min: {df['system_percent'].min():.1f}")
        print(f"  Max: {df['system_percent'].max():.1f}")
        print(f"  Avg: {df['system_percent'].mean():.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        analyze_csv()
    else:
        try:
            asyncio.run(monitor())
        except KeyboardInterrupt:
            print("\nМониторинг остановлен")
            print("\nДля анализа накопленных данных запустите:")
            print(f"  python3 {sys.argv[0]} analyze")
