"""Pydantic schemas for ImageItem API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models.enums import ItemState, ReviewDecision


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    file_path: str
    file_name: str
    state: ItemState
    normalized_caption: str | None
    final_caption: str | None
    generation_prompt: str | None
    provenance: dict[str, Any] | None
    candidate_prompts: list[dict[str, Any]] | None
    raw_analyst_output: dict[str, Any] | None
    warnings: list[dict[str, Any]] | None
    llm_pass_result: dict[str, Any] | None
    decision: ReviewDecision | None
    decision_notes: str | None
    last_error_category: str | None
    last_error_message: str | None
    last_error_at: datetime | None
    normalizer_attempt: int
    created_at: datetime
    updated_at: datetime


class ItemSummary(BaseModel):
    """Compact item info for list/table views."""

    id: int
    file_name: str
    state: ItemState
    decision: ReviewDecision | None
    normalized_caption: str | None
    warning_count: int
    last_error_category: str | None


class DecideRequest(BaseModel):
    decision: ReviewDecision
    notes: str | None = None
    caption: str | None = None  # optional user-edited caption; overrides normalized_caption on ACCEPT


class SaveCaptionRequest(BaseModel):
    caption: str


class MassDecideRequest(BaseModel):
    decision: ReviewDecision
    item_ids: list[int] | None = None  # None → apply to all matching filter
    state_filter: ItemState | None = None  # filter for "all" mode
    include_with_warnings: bool = False  # for ACCEPT: include items with warnings
