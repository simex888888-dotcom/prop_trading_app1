import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Импортируем Base и все модели
from database import Base
import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Берём DATABASE_URL из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Railway даёт URL вида postgresql://... или postgres://...
# Alembic для миграций использует синхронный psycopg2
# Поэтому делаем правильный URL для каждого случая
def get_sync_url(url: str) -> str:
    """Конвертируем любой формат URL в синхронный для Alembic."""
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")
    return url

def get_async_url(url: str) -> str:
    """Конвертируем любой формат URL в асинхронный для приложения."""
    url = url.replace("postgres://", "postgresql+asyncpg://")
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url

SYNC_URL = get_sync_url(DATABASE_URL)
ASYNC_URL = get_async_url(DATABASE_URL)

config.set_main_option("sqlalchemy.url", SYNC_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = ASYNC_URL

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()