"""Database engine and sessionmaker factory.

Supports SQLite (default) and PostgreSQL (via [postgres] extra). Connection URL is
read from the bootstrap config (env var CAPTION_AGENT_DB_URL or settings).

The engine is initialized once via `init_engine(url)` at app startup. Use `get_engine()`
and `get_sessionmaker()` to access them. For test isolation, callers can create independent
engines via `create_engine_from_url(url)`.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    """Enable FK enforcement for SQLite (off by default). Required for ON DELETE CASCADE."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_engine_from_url(url: str, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for a given URL.

    SQLite-specific options applied automatically for the SQLite scheme.
    """
    if url.startswith("sqlite"):
        # check_same_thread=False permits sharing the connection across FastAPI threads;
        # SQLite is per-process-fine for a single-user local app.
        engine = create_engine(
            url, echo=echo, connect_args={"check_same_thread": False}
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, echo=echo)


def init_engine(url: str, *, echo: bool = False) -> Engine:
    """Initialize the process-global engine and sessionmaker.

    Idempotent: re-initializing with the same URL is a no-op. Re-initializing with a
    different URL replaces the global engine (used by tests).
    """
    global _engine, _sessionmaker
    if _engine is not None and str(_engine.url) == url:
        return _engine
    _engine = create_engine_from_url(url, echo=echo)
    _sessionmaker = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
    return _engine


def get_engine() -> Engine:
    """Return the global engine. Must be initialized first via `init_engine()`."""
    if _engine is None:
        raise RuntimeError("Engine not initialized — call init_engine(url) first")
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Return the global sessionmaker. Must be initialized first via `init_engine()`."""
    if _sessionmaker is None:
        raise RuntimeError("Sessionmaker not initialized — call init_engine(url) first")
    return _sessionmaker
