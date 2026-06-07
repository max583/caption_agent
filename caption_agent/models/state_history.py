"""State history models for batches and image items (D-087)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow

if TYPE_CHECKING:
    from .batch import Batch
    from .image_item import ImageItem


class BatchStateHistory(Base):
    """Append-only history of batch state transitions."""

    __tablename__ = "batch_state_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    batch: Mapped[Batch] = relationship("Batch", back_populates="state_history")


class ItemStateHistory(Base):
    """Append-only history of image item state transitions."""

    __tablename__ = "item_state_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_item_id: Mapped[int] = mapped_column(
        ForeignKey("image_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    image_item: Mapped[ImageItem] = relationship(
        "ImageItem", back_populates="state_history"
    )
