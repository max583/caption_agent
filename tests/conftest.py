"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from caption_agent.models import Base
from caption_agent.storage import init_engine, session_scope


@pytest.fixture
def in_memory_db() -> Generator[None, None, None]:
    """Initialize an in-memory SQLite database, create all tables, tear down after test."""
    engine = init_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(in_memory_db: None) -> Generator[Session, None, None]:
    """Yield a session bound to the in-memory DB."""
    with session_scope() as s:
        yield s
