"""Business-process logs (D-087).

Per-batch and per-image lifecycle transitions, user decisions, errors. Viewable in UI Journal,
with manual cleanup and automatic retention by days.

Separate from system/server logs which go to rotating log files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_values, utcnow
from .enums import LogLevel


class BusinessLog(Base):
    """A single business-process log entry."""

    __tablename__ = "business_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    level: Mapped[LogLevel] = mapped_column(
        SAEnum(LogLevel, native_enum=False, length=16, values_callable=enum_values),
        default=LogLevel.INFO,
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional foreign-key-like references for filtering (no FK constraint to preserve logs
    # even if the entity is deleted).
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("image_items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Optional structured payload (e.g. error details, LLM I/O dump path).
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
