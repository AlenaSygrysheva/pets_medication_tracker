#!/bin/sh
set -e

echo "Checking database state..."

python << 'PYEOF'
import asyncio, os, sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def prepare():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.begin() as conn:
            # Проверяем наличие таблицы alembic_version
            r = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version')"
            ))
            has_alembic = r.scalar()

            if has_alembic:
                print("Alembic version table found — normal upgrade.")
                return

            # Проверяем, есть ли уже таблица pets (старая установка без alembic)
            r = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'pets')"
            ))
            has_pets = r.scalar()

            if has_pets:
                # Таблицы уже существуют, но alembic ещё не применялся.
                # Помечаем текущее состояние как 001, чтобы alembic
                # применил только дельту (002: add avatar_path).
                await conn.execute(text(
                    "CREATE TABLE alembic_version "
                    "(version_num VARCHAR(32) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                ))
                await conn.execute(text("INSERT INTO alembic_version VALUES ('001')"))
                print("Legacy database detected — stamped as revision 001.")
            else:
                print("Empty database — full migration will run.")
    finally:
        await engine.dispose()

asyncio.run(prepare())
PYEOF

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
