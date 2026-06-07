"""Alembic env.py — reads target metadata from caption_agent.models.

DB URL is taken from the caption_agent bootstrap config (env var CAPTION_AGENT_DB_URL or default).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from caption_agent.config import get_bootstrap_settings
from caption_agent.models import Base

# Alembic config object.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DB URL from bootstrap settings.
settings = get_bootstrap_settings()
config.set_main_option("sqlalchemy.url", settings.db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
