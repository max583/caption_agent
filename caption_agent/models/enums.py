"""Shared enums for caption agent models.

Stored as VARCHAR in DB (SQLAlchemy native Enum support); Python values are strings.
"""

from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    """Origin of images in a batch (D-085)."""

    SYNTHETIC = "synthetic"
    REFERENCE = "reference"


class BranchType(StrEnum):
    """LoRA branch the captions are intended for (D-070)."""

    IDENTITY = "identity"
    NUDE_BODY_NEUTRAL = "nude_body_neutral"
    ADULT_AROUSED = "adult_aroused"


class LoraType(StrEnum):
    """Type of LoRA the project is training (D-109).

    Determines what the pipeline focuses on when analysing and captioning images.
    """

    CHARACTER = "character"
    CREATURE = "creature"
    STYLE = "style"
    CLOTHING = "clothing"
    POSE = "pose"
    OBJECT = "object"
    FACE = "face"


class BatchState(StrEnum):
    """Batch lifecycle states (D-087)."""

    SCHEDULED = "scheduled"
    QUEUED = "queued"
    SCANNING = "scanning"   # pre-scan: context_reader runs for all items before captioning
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    EXPORTING = "exporting"
    DONE = "done"
    PAUSED = "paused"
    ERROR = "error"


class ItemState(StrEnum):
    """Per-image-item lifecycle states inside a batch (D-087)."""

    QUEUED = "queued"
    READING_CONTEXT = "reading_context"
    ANALYZING = "analyzing"
    NORMALIZING = "normalizing"
    GAP_FILLING = "gap_filling"  # deprecated (D-102) — kept for historical state_history rows
    RULE_CHECK = "rule_check"
    LLM_PASS_CHECK = "llm_pass_check"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REGENERATING = "regenerating"
    DROPPED = "dropped"
    SKIPPED = "skipped"
    EXPORTING = "exporting"
    DONE = "done"
    ERROR = "error"


class ReviewDecision(StrEnum):
    """User decisions during review."""

    ACCEPT = "accept"
    REGENERATE = "regenerate"
    DROP = "drop"
    SKIP = "skip"


class LogLevel(StrEnum):
    """Log levels for business logger."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ErrorCategory(StrEnum):
    """Error categories per D-087."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    POLICY = "policy"
    VALIDATION = "validation"
