"""Session management helpers and FastAPI dependency."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from .connection import get_sessionmaker


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, commits on success, rolls back on exception.

    Usage:
        @app.get("/foo")
        def foo(session: Session = Depends(get_session)) -> ...:
    """
    sessionmaker = get_sessionmaker()
    session = sessionmaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager version of `get_session` for non-FastAPI code (orchestration, tests)."""
    sessionmaker = get_sessionmaker()
    session = sessionmaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
