"""Pydantic schemas for Batch API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import BatchState, BranchType, SourceType


class BatchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_folder_path: str = Field(..., min_length=1)
    source_type: SourceType | None = None  # None → inherit from project
    branch: BranchType | None = None  # None → inherit from project
    schedule_at: datetime | None = None
    normalizer_max_retries_override: int | None = Field(default=None, ge=0)
    consecutive_failure_threshold_override: int | None = Field(default=None, ge=1)


class BatchUpdate(BaseModel):
    """Editable fields after creation (source_folder_path is immutable)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: SourceType | None = None
    branch: BranchType | None = None
    schedule_at: datetime | None = None
    normalizer_max_retries_override: int | None = Field(default=None, ge=0)
    consecutive_failure_threshold_override: int | None = Field(default=None, ge=1)


class BatchStateHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_state: str | None
    to_state: str
    reason: str | None
    changed_at: datetime


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    source_folder_path: str
    source_type: SourceType
    branch: BranchType
    state: BatchState
    schedule_at: datetime | None
    last_state_change_at: datetime | None
    processing_started_at: datetime | None = None
    consecutive_failure_counter: int
    normalizer_max_retries_override: int | None
    consecutive_failure_threshold_override: int | None
    last_error_reason: str | None
    created_at: datetime
    updated_at: datetime

    # Computed stats
    total_items: int = 0
    queued_items: int = 0
    processing_items: int = 0
    awaiting_review_items: int = 0
    approved_items: int = 0
    error_items: int = 0
    done_items: int = 0
    skipped_items: int = 0
    dropped_items: int = 0
    progress_pct: int = 0  # 0-100
    scan_progress: int = 0   # items scanned so far (SCANNING phase)

    state_history: list[BatchStateHistoryOut] = []


class BatchCard(BaseModel):
    """Compact batch summary for the project workspace list."""

    id: int
    name: str
    state: BatchState
    total_items: int
    awaiting_review_items: int
    approved_items: int
    error_items: int
    progress_pct: int
    scan_progress: int
    schedule_at: datetime | None
    last_state_change_at: datetime | None
    last_error_reason: str | None
    # "error" | "review" | "active" | "scanning" | "scheduled" | "idle"
    status_category: str
