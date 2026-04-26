#!/usr/bin/env python3
"""
Скрипт для генерации тестового кода входа для админа
Использование: python scripts/generate_login_code.py [tg_id]
"""

import asyncio
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
import os

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Ошибка: DATABASE_URL не найден в .env")
    sys.exit(1)


async def generate_login_code(tg_id: int) -> str:
    """Генерирует и сохраняет код входа для админа"""

    # Генерируем 8-символный код (буквы + цифры)
    code = secrets.token_urlsafe(6)[:8].upper()

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Проверяем, что tg_id существует в таблице users
        user_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM users WHERE tg_id = $1)",
            tg_id
        )

        if not user_exists:
            print(f"⚠️  Предупреждение: tg_id {tg_id} не найден в таблице users")
            print("   Код может не работать, если пользователь не зарегистрирован в Telegram боте")

        # Вставляем код
        await conn.execute("""
            INSERT INTO login_codes (code, tg_id, expires_at, used)
            VALUES ($1, $2, $3, $4)
        """, code, tg_id, datetime.utcnow() + timedelta(hours=24), False)

        expires_at = datetime.utcnow() + timedelta(hours=24)

        # Логируем результат
        print("\n" + "="*60)
        print("✅ КОД ВХОДА УСПЕШНО СОЗДАН")
        print("="*60)
        print(f"🔐 Код:        {code}")
        print(f"👤 Telegram ID: {tg_id}")
        print(f"⏰ Действует:   до {expires_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
        print(f"🔗 Ссылка для входа:")
        print(f"   https://your-domain.com/?code={code}")
        print("="*60 + "\n")

        return code

    finally:
        await conn.close()


async def main():
    tg_id = int(sys.argv[1]) if len(sys.argv) > 1 else 552810834

    try:
        await generate_login_code(tg_id)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
