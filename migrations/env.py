import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from packages.domain.db import Base
from packages.persistence.database_url import normalize_database_url

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
configured_database_url = config.get_main_option("sqlalchemy.url")
database_url = os.getenv("DATABASE_URL") or configured_database_url
if database_url is None:
    raise RuntimeError("Alembic requires DATABASE_URL or sqlalchemy.url")
config.set_main_option(
    "sqlalchemy.url",
    normalize_database_url(database_url),
)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section)
    if section is None:
        raise RuntimeError("Alembic configuration section is missing")
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
