"""Batch ORM model — one source folder of images going through the pipeline (D-087)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, enum_values
from .enums import BatchState, BranchType, SourceType

if TYPE_CHECKING:
    from .image_item import ImageItem
    from .project import Project
    from .state_history import BatchStateHistory


class Batch(Base, TimestampMixin):
    """A single captioning campaign over one source folder. Belongs to a Project (D-087)."""

    __tablename__ = "batches"
    # Monotonic IDs: never reuse a deleted batch's id (defense for URLs/refs).
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_folder_path: Mapped[str] = mapped_column(Text, nullable=False)

    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, native_enum=False, length=32, values_callable=enum_values),
        default=SourceType.SYNTHETIC,
        nullable=False,
    )
    branch: Mapped[BranchType] = mapped_column(
        SAEnum(BranchType, native_enum=False, length=32, values_callable=enum_values),
        default=BranchType.IDENTITY,
        nullable=False,
    )

    state: Mapped[BatchState] = mapped_column(
        SAEnum(BatchState, native_enum=False, length=32, values_callable=enum_values),
        default=BatchState.QUEUED,
        nullable=False,
        index=True,
    )
    last_state_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # One-shot scheduling per D-087.
    schedule_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Per-batch error tracking.
    consecutive_failure_counter: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Per-batch retry limit overrides (NULL = inherit from global config).
    normalizer_max_retries_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecutive_failure_threshold_override: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Optional last error reason for batch-level Error state.
    last_error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Progress counter for the SCANNING phase (0..total_items).
    scan_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Set on the first transition to PROCESSING; never reset on pause/resume (D-103).
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped[Project] = relationship("Project", back_populates="batches")
    image_items: Mapped[list[ImageItem]] = relationship(
        "ImageItem",
        back_populates="batch",
        cascade="all, delete-orphan",
    )
    state_history: Mapped[list[BatchStateHistory]] = relationship(
        "BatchStateHistory",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="BatchStateHistory.changed_at",
    )

    def __repr__(self) -> str:
        return f"<Batch id={self.id} name={self.name!r} state={self.state}>"
