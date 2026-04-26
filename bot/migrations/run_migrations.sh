#!/bin/bash
# ============================================================================
# Скрипт применения миграций базы данных
# ============================================================================
# Использование:
#   ./run_migrations.sh [OPTIONS]
#
# Опции:
#   --dry-run     Показать, что будет сделано, без выполнения
#   --rollback    Откатить последнюю миграцию
#   --help        Показать справку
#
# Переменные окружения:
#   DATABASE_URL  URL подключения к БД (обязательно)
# ============================================================================

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Пути
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"
ROLLBACK_DIR="${SCRIPT_DIR}/migrations/rollback"
LOG_FILE="${SCRIPT_DIR}/migrations_$(date +%Y%m%d_%H%M%S).log"

# Флаги
DRY_RUN=false
ROLLBACK=false

# ============================================================================
# Функции
# ============================================================================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1" >&2
}

show_help() {
    cat << EOF
Скрипт применения миграций базы данных

Использование:
    $0 [OPTIONS]

Опции:
    --dry-run     Показать, что будет сделано, без выполнения
    --rollback    Откатить последнюю миграцию
    --help        Показать эту справку

Примеры:
    $0                          # Применить все миграции
    $0 --dry-run                # Показать план без выполнения
    $0 --rollback               # Откатить последнюю миграцию

Переменные окружения:
    DATABASE_URL    URL подключения к БД
                    Пример: postgresql://user:pass@localhost:5432/dbname

EOF
}

check_database_url() {
    if [[ -z "${DATABASE_URL:-}" ]]; then
        error "Переменная окружения DATABASE_URL не установлена"
        echo ""
        echo "Установите её:"
        echo "    export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'"
        echo ""
        exit 1
    fi
    success "DATABASE_URL установлен"
}

check_connection() {
    log "Проверка подключения к БД..."
    if ! psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
        error "Не удалось подключиться к базе данных"
        exit 1
    fi
    success "Подключение к БД успешно"
}

create_backup() {
    log "Создание бэкапа базы данных..."
    local backup_file="${SCRIPT_DIR}/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if psql "$DATABASE_URL" -c "SELECT version()" | grep -q "PostgreSQL"; then
        pg_dump "$DATABASE_URL" > "$backup_file" 2>/dev/null
        success "Бэкап создан: $backup_file"
        echo "$backup_file"
    else
        warning "Не удалось создать бэкап (pg_dump недоступен)"
        echo ""
    fi
}

run_migration() {
    local migration_file="$1"
    local filename=$(basename "$migration_file")
    
    log "Применение миграции: $filename"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "    [DRY-RUN] Будет выполнен: psql -f $migration_file"
    else
        if psql "$DATABASE_URL" -f "$migration_file" 2>&1 | tee -a "$LOG_FILE"; then
            success "Миграция применена: $filename"
        else
            error "Ошибка применения миграции: $filename"
            return 1
        fi
    fi
}

run_rollback() {
    local rollback_file="$1"
    local filename=$(basename "$rollback_file")
    
    warning "Откат миграции: $filename"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "    [DRY-RUN] Будет выполнен: psql -f $rollback_file"
    else
        if psql "$DATABASE_URL" -f "$rollback_file" 2>&1 | tee -a "$LOG_FILE"; then
            success "Откат выполнен: $filename"
        else
            error "Ошибка отката: $filename"
            return 1
        fi
    fi
}

get_last_migration() {
    ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -n1
}

# ============================================================================
# Основная логика
# ============================================================================

main() {
    echo "============================================================================"
    echo "Миграция базы данных"
    echo "============================================================================"
    echo ""
    
    # Парсинг аргументов
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "Неизвестная опция: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Проверки
    check_database_url
    check_connection
    
    if [[ "$ROLLBACK" == "true" ]]; then
        # Откат
        warning "РЕЖИМ ОТКАТА"
        echo ""
        
        last_migration=$(get_last_migration)
        if [[ -z "$last_migration" ]]; then
            error "Нет файлов миграций в $MIGRATIONS_DIR"
            exit 1
        fi
        
        migration_name=$(basename "$last_migration" .sql)
        rollback_file="${ROLLBACK_DIR}/${migration_name}.sql"
        
        if [[ ! -f "$rollback_file" ]]; then
            error "Файл отката не найден: $rollback_file"
            exit 1
        fi
        
        log "Последняя миграция: $migration_name"
        log "Файл отката: $rollback_file"
        echo ""
        
        if [[ "$DRY_RUN" != "true" ]]; then
            read -p "Продолжить? (да/нет): " confirm
            if [[ "$confirm" != "да" && "$confirm" != "y" ]]; then
                log "Отменено пользователем"
                exit 0
            fi
        fi
        
        run_rollback "$rollback_file"
        
    else
        # Применение миграций
        if [[ "$DRY_RUN" == "true" ]]; then
            warning "РЕЖИМ ПРОВЕРКИ (без выполнения)"
        else
            warning "РЕЖИМ ПРИМЕНЕНИЯ"
            echo ""
            
            # Создание бэкапа
            backup_file=$(create_backup)
        fi
        
        echo ""
        log "Поиск миграций в: $MIGRATIONS_DIR"
        echo ""
        
        # Находим все миграции и сортируем
        migrations=($(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | grep -E '^[0-9]+' | sort -V))
        
        if [[ ${#migrations[@]} -eq 0 ]]; then
            error "Миграции не найдены в $MIGRATIONS_DIR"
            exit 1
        fi
        
        log "Найдено миграций: ${#migrations[@]}"
        echo ""
        
        # Применяем по порядку
        for migration in "${migrations[@]}"; do
            run_migration "$migration" || {
                error "Применение миграции прервано"
                exit 1
            }
            echo ""
        done
        
        success "Все миграции применены успешно"
        
        if [[ "$DRY_RUN" != "true" ]]; then
            echo ""
            log "Лог сохранен: $LOG_FILE"
        fi
    fi
    
    echo ""
    echo "============================================================================"
}

# Запуск
main "$@"
