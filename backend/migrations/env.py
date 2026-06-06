"""Alembic environment configuration.

비동기(asyncpg) 드라이버를 사용하므로 run_migrations_online은
asyncio + run_sync 패턴으로 실행합니다.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 모든 모델을 import해야 autogenerate가 정상 동작합니다.
import app.models  # noqa: F401
from app.db.session import Base

# Alembic Config object
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 마이그레이션 대상 메타데이터
target_metadata = Base.metadata


def get_url() -> str:
    """환경변수 DATABASE_URL에서 URL을 읽어 sync 드라이버로 변환."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://hierardo:hierardo@localhost:5432/hierardo",
    )
    # alembic은 sync 드라이버로 실행 (asyncpg → psycopg2 폴백 없이 async 방식 사용)
    return url


def run_migrations_offline() -> None:
    """오프라인 모드: SQL 스크립트만 생성."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 엔진으로 마이그레이션 실행."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
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
