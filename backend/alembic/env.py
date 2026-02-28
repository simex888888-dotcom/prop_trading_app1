import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Добавляем backend/ в sys.path для импорта app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base  # noqa: E402

# Импортируем все модели, чтобы alembic видел metadata
from app.models import (  # noqa: F401, E402
    User, ChallengeType, UserChallenge, Trade, Violation,
    Payout, Achievement, UserAchievement, Referral, Notification, ScalingStep
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    raw = os.getenv("DATABASE_URL", "")
    if not raw:
        # Строим из компонентов
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "password")
        name = os.getenv("DB_NAME", "chm_krypton")
        raw = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    raw = raw.replace("postgresql+asyncpg://", "postgresql://")
    raw = raw.replace("postgres://", "postgresql://")
    return raw


def _get_async_url(sync_url: str) -> str:
    url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    return url


SYNC_URL = _get_sync_url()
ASYNC_URL = _get_async_url(SYNC_URL)

config.set_main_option("sqlalchemy.url", SYNC_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
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
