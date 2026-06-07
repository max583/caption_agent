"""Per-project caption policy config (D-114).

CaptionPolicyConfig holds the per-project caption policy.  A project with
caption_policy=NULL in the DB uses project defaults via get_project_policy().
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from caption_agent.config.policy_defaults import (
    DEFAULT_COARSE_SETTING_NOTE,
    DEFAULT_IDENTITY_TRAIT_PATTERNS,
    DEFAULT_SETTING_OVERSPECIFIC_PHRASES,
    DEFAULT_SOURCE_REF_REQUIRED_SETTING,
)

if TYPE_CHECKING:
    from caption_agent.models.project import Project


class CaptionPolicyConfig(BaseModel):
    """Per-project caption policy (D-114).

    Structured fields are consumed by rule_checker (machine-readable).
    Free-text fields are injected into LLM prompts.
    NULL caption_policy on a Project → project defaults (backward compat).
    """

    model_config = ConfigDict(extra="ignore")

    # Machine-readable: rule_checker builds regexes from these patterns.
    identity_trait_patterns: list[str] = Field(
        default_factory=lambda: list(DEFAULT_IDENTITY_TRAIT_PATTERNS)
    )
    # Machine-readable: rule_checker does substring matching on these phrases.
    setting_overspecific_phrases: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SETTING_OVERSPECIFIC_PHRASES)
    )
    # Machine-readable: rule_checker exact-matches this token in source-ref captions.
    source_ref_required_setting: str = DEFAULT_SOURCE_REF_REQUIRED_SETTING

    # Free-text: injected into normalizer prompt as coarse-setting guidance.
    coarse_setting_note: str = DEFAULT_COARSE_SETTING_NOTE

    # Free-text: optional extra rules appended to normalizer / checker prompts.
    custom_normalizer_rules: str | None = None
    custom_checker_rules: str | None = None


def get_project_policy(project: "Project") -> CaptionPolicyConfig:
    """Return the project's caption policy, falling back to project defaults if null."""
    if project.caption_policy is None:
        return CaptionPolicyConfig()
    return CaptionPolicyConfig.model_validate(project.caption_policy)
