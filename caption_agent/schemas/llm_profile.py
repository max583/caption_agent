"""Pydantic schemas for LLM configuration profiles."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..config.schema import LLMConfig, StepLLMOverride


class LLMProfileSnapshot(BaseModel):
    """The three LLM config blocks stored together in a profile.

    Matches the keys in the `configuration` table:
    ``llm``, ``llm_analyst``, ``llm_normalizer``, ``llm_checker``.

    extra='ignore' so old saved profiles that contain ``llm_gap_filler`` (removed in D-102)
    do not crash validation.
    """

    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    llm_analyst: StepLLMOverride = Field(default_factory=StepLLMOverride)
    llm_normalizer: StepLLMOverride = Field(default_factory=StepLLMOverride)
    llm_checker: StepLLMOverride = Field(default_factory=StepLLMOverride)


class LLMProfileOut(BaseModel):
    """API response schema for a profile."""

    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    snapshot: LLMProfileSnapshot

    model_config = {"from_attributes": True}


class LLMProfileCreate(BaseModel):
    """Body for POST /api/llm-profiles.

    If ``snapshot`` is omitted, the server snapshots the current flat config.
    """

    name: str
    description: str | None = None
    snapshot: LLMProfileSnapshot | None = None


class LLMProfileUpdate(BaseModel):
    """Partial update body for PATCH /api/llm-profiles/{id}."""

    name: str | None = None
    description: str | None = None
    snapshot: LLMProfileSnapshot | None = None
