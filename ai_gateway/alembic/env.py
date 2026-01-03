from __future__ import with_statement

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
import ai_gateway.db as db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
try:
    if config.config_file_name:
        fileConfig(config.config_file_name)
except Exception:
    # If logging sections are missing in the ini, ignore logging setup
    pass

# add your model's MetaData object here
target_metadata = db.Base.metadata


def get_url():
    # prefer AI_GATEWAY_DB env var (can be full URL), fallback to SQLALCHEMY URL in ini
    return os.getenv("AI_GATEWAY_DB") or config.get_main_option("sqlalchemy.url")


def get_version_table():
    try:
        return config.get_main_option("version_table")
    except Exception:
        return None


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table=get_version_table(),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=get_version_table(),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
