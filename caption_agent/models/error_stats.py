"""Per-image error counters by category (D-087)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .image_item import ImageItem


class ImageItemErrorStats(Base):
    """Counters for the four error categories per image item.

    Categories per D-087: transient, permanent, policy, validation.
    """

    __tablename__ = "image_item_error_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_item_id: Mapped[int] = mapped_column(
        ForeignKey("image_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    transient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    permanent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    policy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    image_item: Mapped[ImageItem] = relationship(
        "ImageItem", back_populates="error_stats"
    )
