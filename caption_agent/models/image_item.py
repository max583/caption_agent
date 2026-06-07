"""ImageItem ORM model — single image with its own lifecycle inside a batch (D-087)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, enum_values
from .enums import ItemState, ReviewDecision

if TYPE_CHECKING:
    from .batch import Batch
    from .error_stats import ImageItemErrorStats
    from .state_history import ItemStateHistory


class ImageItem(Base, TimestampMixin):
    """Per-image lifecycle and caption artifacts (D-087)."""

    __tablename__ = "image_items"
    __table_args__ = (
        # An item is the unique processing record for one file within one batch.
        # Enforces at the DB level what scan_batch only checked in app code, making
        # re-scan idempotent and preventing duplicate rows for the same image.
        UniqueConstraint("batch_id", "file_path", name="uq_image_items_batch_file"),
        # Monotonic IDs: never reuse a deleted item's id. The item id appears in
        # the /api/items/{id}/image URL; reuse caused the browser to show a prior
        # batch's cached image for a new item under the same URL.
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Filename relative to batch source folder for display purposes.
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    state: Mapped[ItemState] = mapped_column(
        SAEnum(ItemState, native_enum=False, length=32, values_callable=enum_values),
        default=ItemState.QUEUED,
        nullable=False,
        index=True,
    )

    # Pipeline outputs.
    raw_analyst_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    normalized_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Provenance extracted from PNG.
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # All candidate prompt texts extracted from metadata, for human reference at review time (D-102).
    # Shape: [{"label": str, "text": str, "likely_negative": bool}, ...]
    candidate_prompts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Warnings (list of dict) from RuleChecker and LLMPassChecker. JSON list.
    warnings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # LLM-pass checker result blob.
    llm_pass_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # User decision and notes.
    decision: Mapped[ReviewDecision | None] = mapped_column(
        SAEnum(ReviewDecision, native_enum=False, length=32, values_callable=enum_values),
        nullable=True,
    )
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Last error message for ERROR state.
    last_error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When the last error was recorded — lets the UI distinguish stale vs fresh errors.
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Normalizer self-retry attempt counter (resets on success).
    normalizer_attempt: Mapped[int] = mapped_column(default=0, nullable=False)

    batch: Mapped[Batch] = relationship("Batch", back_populates="image_items")
    state_history: Mapped[list[ItemStateHistory]] = relationship(
        "ItemStateHistory",
        back_populates="image_item",
        cascade="all, delete-orphan",
        order_by="ItemStateHistory.changed_at",
    )
    error_stats: Mapped[ImageItemErrorStats | None] = relationship(
        "ImageItemErrorStats",
        back_populates="image_item",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ImageItem id={self.id} file={self.file_name!r} state={self.state}>"
