#!/usr/bin/env python3
"""
Reset and initialize the dev database.

Usage:
    python scripts/init_dev_db.py
    python scripts/init_dev_db.py --env .env.dev

Behavior:
    1. Reads DATABASE_URL from the specified .env file (default: .env.dev).
    2. Connects to the 'postgres' maintenance DB.
    3. Drops & creates the dev DB.
    4. Applies bot/assets/schema_fixed.sql.
    5. Applies web/migrations/*.sql except *drop* files.

This script is safe for dev only — it drops the target database.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env.dev"
SCHEMA_PATH = PROJECT_ROOT / "bot" / "assets" / "schema_fixed.sql"
MIGRATIONS_DIR = PROJECT_ROOT / "web" / "migrations"


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def derive_dsn(original_dsn: str) -> tuple[str, str, str]:
    """Return (maintenance_dsn, target_dsn, target_db_name)."""
    # Example: postgresql://user:pass@host:port/dbname
    match = re.match(r"^(postgresql://[^:]+:[^@]+@[^/]+)/(\w+)$", original_dsn)
    if not match:
        raise ValueError(f"Cannot parse DATABASE_URL: {original_dsn}")
    base = match.group(1)
    db_name = match.group(2)
    maintenance_dsn = f"{base}/postgres"
    return maintenance_dsn, original_dsn, db_name


async def apply_sql(conn: asyncpg.Connection, sql: str, label: str) -> None:
    try:
        await conn.execute(sql)
        print(f"    ok: {label}")
    except Exception as e:
        print(f"    warning: failed to apply {label}: {e}")


async def main() -> int:
    env_path_str = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--env" else DEFAULT_ENV_PATH
    env_path = Path(env_path_str)
    env = load_env(env_path)
    original_dsn = env.get("DATABASE_URL")
    if not original_dsn:
        print(f"ERROR: DATABASE_URL not found in {env_path}")
        return 1

    maintenance_dsn, target_dsn, target_db_name = derive_dsn(original_dsn)

    print(f"Env file:         {env_path}")
    print(f"Target DB DSN:    {target_dsn}")
    print(f"Maintenance DSN:  {maintenance_dsn}")
    print(f"Target DB name:   {target_db_name}")

    # Read schema
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_PATH}")
        return 1
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    # Connect to maintenance DB to recreate target DB
    conn = await asyncpg.connect(maintenance_dsn)
    try:
        print(f"\nRecreating database '{target_db_name}'...")
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{target_db_name}'
              AND pid <> pg_backend_pid()
            """
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{target_db_name}"')
        await conn.execute(f'CREATE DATABASE "{target_db_name}"')
        print(f"  database '{target_db_name}' created.")
    finally:
        await conn.close()

    # Apply schema
    conn = await asyncpg.connect(target_dsn)
    try:
        print(f"\nApplying schema from {SCHEMA_PATH}...")
        await apply_sql(conn, schema_sql, "schema_fixed.sql")

        # Apply web migrations
        if MIGRATIONS_DIR.exists():
            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
            if migration_files:
                print(f"\nApplying web migrations from {MIGRATIONS_DIR}...")
                for migration_path in migration_files:
                    name = migration_path.name
                    if "drop" in name.lower():
                        print(f"  skip (drop migration): {name}")
                        continue
                    migration_sql = migration_path.read_text(encoding="utf-8")
                    await apply_sql(conn, migration_sql, name)
    finally:
        await conn.close()

    print("\nDev database is ready.")
    print(f"  DATABASE_URL: {target_dsn}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
