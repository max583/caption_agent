"""Project ORM model — top-level entity in the data hierarchy (D-087)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, enum_values
from .enums import BranchType, LoraType, SourceType

if TYPE_CHECKING:
    from .batch import Batch


class Project(Base, TimestampMixin):
    """A grouping of related batches. Created manually before adding batches (D-087)."""

    __tablename__ = "projects"
    # Monotonic IDs: never reuse a deleted project's id (defense for URLs/refs).
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Trigger token (LoRA activation word) — unique per LoRA / per project.
    trigger_token: Mapped[str] = mapped_column(
        String(128), default="p3rs0n4", nullable=False
    )

    # Defaults inherited by new batches in this project.
    default_source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, native_enum=False, length=32, values_callable=enum_values),
        default=SourceType.SYNTHETIC,
        nullable=False,
    )
    default_branch: Mapped[BranchType] = mapped_column(
        SAEnum(BranchType, native_enum=False, length=32, values_callable=enum_values),
        default=BranchType.IDENTITY,
        nullable=False,
    )
    default_output_policy: Mapped[str] = mapped_column(
        String(64), default="source_folder", nullable=False
    )

    # LoRA type and base model — used to parameterise pipeline prompts (D-109).
    lora_type: Mapped[LoraType] = mapped_column(
        SAEnum(LoraType, native_enum=False, length=32, values_callable=enum_values),
        default=LoraType.CHARACTER,
        nullable=False,
    )
    base_model_family: Mapped[str] = mapped_column(
        String(64), default="flux", nullable=False
    )

    # Per-project caption policy (D-114). NULL → project defaults via get_project_policy().
    caption_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationship: cascade delete (D-087 — Project deletion removes batches and items in DB
    # but does NOT touch source files or exported .txt sidecars on disk).
    # cascade="all, delete-orphan" makes SQLAlchemy issue explicit child DELETEs
    # AND keep its identity map consistent. DB-level FK cascade is also enabled
    # (SQLite foreign_keys PRAGMA, PostgreSQL native) as defense-in-depth.
    batches: Mapped[list[Batch]] = relationship(
        "Batch",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
