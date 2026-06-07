"""Declarative base for SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return timezone-aware UTC now. Used as default for created_at columns."""
    return datetime.now(timezone.utc)


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """``values_callable`` for ``SAEnum`` so the DB stores the StrEnum ``.value``
    (e.g. ``"error"``), not the member *name* (``"ERROR"``).

    Without this, ``SAEnum(native_enum=False)`` persists the member name, which
    (a) mismatches the ``*_state_history`` String columns that already store
    ``.value``, and (b) breaks raw-SQL filters like ``state = 'error'``. Keeping
    the stored form equal to ``.value`` makes DB, ORM, and JSON all agree.
    """
    return [member.value for member in enum_cls]


class Base(DeclarativeBase):
    """Declarative base. Adds created_at / updated_at to all tables via mixin in subclasses."""


class TimestampMixin:
    """Mixin providing created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
