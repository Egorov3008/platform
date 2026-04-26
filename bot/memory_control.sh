#!/bin/bash
# Управление мониторингом памяти
# Использование: ./memory_control.sh [start|stop|status|analyze]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.memory_monitor.pid"
LOG_FILE="$SCRIPT_DIR/memory_monitor.log"
CSV_FILE="$SCRIPT_DIR/memory_monitor.csv"
VENV="$SCRIPT_DIR/venv/bin/activate"

start_monitor() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "❌ Мониторинг уже запущен (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
    source "$VENV"
    nohup python3 memory_monitor.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ Мониторинг запущен (PID: $(cat $PID_FILE))"
        echo "📊 Лог файл: $LOG_FILE"
        echo "📈 CSV файл: $CSV_FILE"
        echo ""
        echo "Последние данные:"
        tail -5 "$LOG_FILE" | grep -E "^[0-9]{2}:" || echo "Ожидание первых данных..."
    else
        echo "❌ Не удалось запустить мониторинг"
        cat "$LOG_FILE"
        return 1
    fi
}

stop_monitor() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "✅ Мониторинг остановлен (PID: $PID)"
            rm -f "$PID_FILE"
        else
            echo "❌ Процесс не найден (PID: $PID)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ PID файл не найден. Мониторинг не запущен?"
        # Попробуем найти процесс
        PGREP=$(pgrep -f "memory_monitor.py")
        if [ -n "$PGREP" ]; then
            echo "Найден процесс: $PGREP"
            read -p "Убить процесс? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                kill $PGREP
                echo "✅ Процесс убит"
            fi
        fi
    fi
}

status_monitor() {
    echo "=== Статус мониторинга ==="
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Запущен (PID: $PID)"
        else
            echo "❌ Процесс мёртв (PID: $PID)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ Не запущен"
    fi
    
    echo ""
    echo "=== Файлы ==="
    [ -f "$LOG_FILE" ] && echo "📄 Лог: $LOG_FILE ($(wc -l < $LOG_FILE) строк)" || echo "📄 Лог: не найден"
    [ -f "$CSV_FILE" ] && echo "📈 CSV: $CSV_FILE ($(wc -l < $CSV_FILE) записей)" || echo "📈 CSV: не найден"
    
    echo ""
    echo "=== Последние данные ==="
    if [ -f "$CSV_FILE" ] && [ $(wc -l < $CSV_FILE) -gt 1 ]; then
        echo "Последние 5 записей:"
        tail -5 "$CSV_FILE" | column -t -s','
    fi
}

analyze_data() {
    echo "=== Анализ данных ==="
    
    if [ ! -f "$CSV_FILE" ]; then
        echo "❌ CSV файл не найден"
        return 1
    fi
    
    RECORDS=$(wc -l < "$CSV_FILE")
    if [ "$RECORDS" -lt 2 ]; then
        echo "❌ Недостаточно данных (минимум 2 записи, есть: $RECORDS)"
        return 1
    fi
    
    source "$VENV"
    python3 << EOF
import pandas as pd
import sys

df = pd.read_csv('$CSV_FILE')

# Конвертируем в числа
for col in ['bot_rss_mb', 'bot_vms_mb', 'bot_memory_percent', 'system_percent', 'swap_percent']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print(f"\nЗаписей: {len(df)}")
print(f"Период: {df['timestamp'].iloc[0]} — {df['timestamp'].iloc[-1]}")

if len(df) >= 2:
    first = df['bot_rss_mb'].iloc[0]
    last = df['bot_rss_mb'].iloc[-1]
    trend = last - first
    duration_hours = (len(df) * 10) / 3600  # 10 сек интервал
    
    print(f"\n📊 Память бота (RSS):")
    print(f"  Start: {first:.2f} MB")
    print(f"  End:   {last:.2f} MB")
    print(f"  Trend: {trend:+.2f} MB ({trend/first*100:+.1f}%)")
    if duration_hours > 0:
        print(f"  Rate:  {trend/duration_hours:+.2f} MB/час")
    
    print(f"\n📊 Системная память:")
    print(f"  Min: {df['system_percent'].min():.1f}%")
    print(f"  Max: {df['system_percent'].max():.1f}%")
    print(f"  Avg: {df['system_percent'].mean():.1f}%")
    
    print(f"\n📊 Swap:")
    print(f"  Min: {df['swap_percent'].min():.1f}%")
    print(f"  Max: {df['swap_percent'].max():.1f}%")
    print(f"  Avg: {df['swap_percent'].mean():.1f}%")
    
    # Оценка
    print("\n" + "="*50)
    if abs(trend) > 50:
        if trend > 0:
            print("⚠️  ОБНАРУЖЕН РОСТ ПАМЯТИ - возможна утечка!")
        else:
            print("✓ Память уменьшается - возможна сборка мусора")
    else:
        print("✓ Память стабильна (изменение < 50 MB)")
    
    if df['system_percent'].mean() > 80:
        print("⚠️  СИСТЕМА ПЕРЕГРУЖЕНА (>80% памяти)")
    
    if df['swap_percent'].mean() > 40:
        print("⚠️  SWAP АКТИВЕН (>40%)")
EOF
}

show_help() {
    echo "Управление мониторингом памяти"
    echo ""
    echo "Использование:"
    echo "  $0 start    - Запустить мониторинг"
    echo "  $0 stop     - Остановить мониторинг"
    echo "  $0 status   - Показать статус"
    echo "  $0 analyze  - Анализ накопленных данных"
    echo "  $0 help     - Эта справка"
    echo ""
    echo "Примеры:"
    echo "  $0 start              # Запустить на 24 часа"
    echo "  $0 status             # Проверить статус"
    echo "  $0 analyze            # Анализ после 24 часов"
    echo "  $0 stop               # Остановить"
}

case "${1:-status}" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    status)
        status_monitor
        ;;
    analyze)
        analyze_data
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac
