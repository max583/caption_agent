"""Pydantic schemas for Project API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import BranchType, LoraType, SourceType


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    trigger_token: str = Field(default="p3rs0n4", min_length=1, max_length=128)
    default_source_type: SourceType = SourceType.SYNTHETIC
    default_branch: BranchType = BranchType.IDENTITY
    default_output_policy: str = "source_folder"
    lora_type: LoraType = LoraType.CHARACTER
    base_model_family: str = "flux"
    caption_policy: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    trigger_token: str | None = Field(default=None, min_length=1, max_length=128)
    default_source_type: SourceType | None = None
    default_branch: BranchType | None = None
    default_output_policy: str | None = None
    lora_type: LoraType | None = None
    base_model_family: str | None = None
    caption_policy: dict[str, Any] | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    trigger_token: str
    default_source_type: SourceType
    default_branch: BranchType
    default_output_policy: str
    lora_type: LoraType
    base_model_family: str
    caption_policy: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    # Computed stats (populated by the router from DB queries)
    total_batches: int = 0
    active_batches: int = 0
    error_batches: int = 0
    awaiting_review_batches: int = 0
    awaiting_review_items: int = 0
    last_activity_at: datetime | None = None


class ProjectCard(BaseModel):
    """Compact project summary for the projects-list page."""

    id: int
    name: str
    description: str | None
    total_batches: int
    active_batches: int
    error_batches: int
    awaiting_review_batches: int
    awaiting_review_items: int
    last_activity_at: datetime | None
    # "error" | "review" | "active" | "idle"
    status_category: str
