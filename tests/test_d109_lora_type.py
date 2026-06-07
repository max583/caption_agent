"""Tests for D-109 Track A: LoraType enum, Project columns, prompt loader, pipeline wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

# Import config.manager first to avoid the pre-existing circular import between
# caption_agent.schemas.llm_profile and caption_agent.config.manager.
from caption_agent.config.manager import ConfigManager  # noqa: F401
from caption_agent.models import Project
from caption_agent.models.enums import LoraType
from caption_agent.pipeline._prompts import load_prompt_with_context
from caption_agent.schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate


# ---------------------------------------------------------------------------
# Step 1 — LoraType enum
# ---------------------------------------------------------------------------


def test_lora_type_values() -> None:
    assert LoraType.CHARACTER == "character"
    assert LoraType.CREATURE == "creature"
    assert LoraType.STYLE == "style"
    assert LoraType.CLOTHING == "clothing"
    assert LoraType.POSE == "pose"
    assert LoraType.OBJECT == "object"
    assert LoraType.FACE == "face"


def test_lora_type_all_members() -> None:
    members = {lt.value for lt in LoraType}
    assert members == {"character", "creature", "style", "clothing", "pose", "object", "face"}


def test_lora_type_is_str() -> None:
    """LoraType values must be plain strings (StrEnum)."""
    assert isinstance(LoraType.CHARACTER, str)
    assert LoraType.CHARACTER == "character"


# ---------------------------------------------------------------------------
# Step 2 — Project model columns with defaults
# ---------------------------------------------------------------------------


def test_project_lora_type_default(session: Session) -> None:
    project = Project(name="test-lora-default", trigger_token="tok1")
    session.add(project)
    session.flush()
    assert project.lora_type == LoraType.CHARACTER
    assert project.base_model_family == "flux"


def test_project_lora_type_set(session: Session) -> None:
    project = Project(name="test-lora-style", trigger_token="tok2", lora_type=LoraType.STYLE, base_model_family="sdxl")
    session.add(project)
    session.flush()
    assert project.lora_type == LoraType.STYLE
    assert project.base_model_family == "sdxl"


def test_project_existing_data_unaffected(session: Session) -> None:
    """Migration default: existing projects without lora_type columns get 'character'/'flux'."""
    project = Project(name="test-lora-migration", trigger_token="tok3")
    session.add(project)
    session.flush()
    # Default values must not require explicit setting
    assert project.lora_type == LoraType.CHARACTER
    assert project.base_model_family == "flux"


# ---------------------------------------------------------------------------
# Step 4 — Pydantic schemas
# ---------------------------------------------------------------------------


def test_project_create_defaults() -> None:
    schema = ProjectCreate(name="my-project")
    assert schema.lora_type == LoraType.CHARACTER
    assert schema.base_model_family == "flux"


def test_project_create_style_lora() -> None:
    schema = ProjectCreate(name="style-lora", lora_type="style", base_model_family="sdxl")
    assert schema.lora_type == LoraType.STYLE
    assert schema.base_model_family == "sdxl"


@pytest.mark.parametrize("lora_type_val", [lt.value for lt in LoraType])
def test_project_create_all_lora_types(lora_type_val: str) -> None:
    schema = ProjectCreate(name=f"proj-{lora_type_val}", lora_type=lora_type_val)
    assert schema.lora_type == lora_type_val


def test_project_create_invalid_lora_type() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="bad", lora_type="nonexistent_type")


def test_project_update_lora_type() -> None:
    update = ProjectUpdate(lora_type="clothing")
    assert update.lora_type == LoraType.CLOTHING


def test_project_update_all_none_by_default() -> None:
    update = ProjectUpdate()
    assert update.lora_type is None
    assert update.base_model_family is None


def test_project_out_includes_lora_fields(session: Session) -> None:
    project = Project(name="test-out", trigger_token="tok4", lora_type=LoraType.FACE, base_model_family="hunyuan")
    session.add(project)
    session.flush()
    session.refresh(project)
    out = ProjectOut.model_validate(project)
    assert out.lora_type == LoraType.FACE
    assert out.base_model_family == "hunyuan"


# ---------------------------------------------------------------------------
# Step 5 — load_prompt_with_context
# ---------------------------------------------------------------------------


def test_load_prompt_with_context_substitutes_trigger(tmp_path: "Path") -> None:
    template = "{trigger_token}, full shot, front view."
    prompt_file = tmp_path / "test_prompt.txt"
    prompt_file.write_text(template, encoding="utf-8")

    with patch("caption_agent.pipeline._prompts._PROMPTS_DIR", tmp_path):
        result = load_prompt_with_context("test_prompt.txt", trigger_token="abc123")
    assert result == "abc123, full shot, front view."


def test_load_prompt_with_context_substitutes_lora_type(tmp_path: "Path") -> None:
    template = "You are processing a {lora_type} LoRA dataset."
    prompt_file = tmp_path / "test_prompt2.txt"
    prompt_file.write_text(template, encoding="utf-8")

    with patch("caption_agent.pipeline._prompts._PROMPTS_DIR", tmp_path):
        result = load_prompt_with_context("test_prompt2.txt", trigger_token="tok", lora_type="style")
    assert result == "You are processing a style LoRA dataset."


def test_load_prompt_with_context_both_substituted(tmp_path: "Path") -> None:
    template = "{trigger_token} — {lora_type} LoRA."
    prompt_file = tmp_path / "both.txt"
    prompt_file.write_text(template, encoding="utf-8")

    with patch("caption_agent.pipeline._prompts._PROMPTS_DIR", tmp_path):
        result = load_prompt_with_context("both.txt", trigger_token="mychar01", lora_type="character")
    assert result == "mychar01 — character LoRA."


def test_load_prompt_with_context_noop_on_real_templates(tmp_path: "Path") -> None:
    """Current real templates have no {lora_type} — substitution must be a no-op."""
    template = "{trigger_token}, full shot, front view, wearing a coat."
    prompt_file = tmp_path / "normalizer_system.txt"
    prompt_file.write_text(template, encoding="utf-8")

    with patch("caption_agent.pipeline._prompts._PROMPTS_DIR", tmp_path):
        result = load_prompt_with_context("normalizer_system.txt", "mytoken", "style")
    # lora_type substitution is a no-op; trigger_token is replaced
    assert result == "mytoken, full shot, front view, wearing a coat."


# ---------------------------------------------------------------------------
# Step 6 — Pipeline step signatures accept lora_type
# ---------------------------------------------------------------------------


def test_normalizer_run_accepts_lora_type() -> None:
    """normalizer.run must accept lora_type kwarg without TypeError."""
    from caption_agent.pipeline import normalizer

    item = MagicMock()
    item.batch = MagicMock()
    item.batch.source_type.value = "synthetic"
    item.batch.branch.value = "identity"
    item.raw_analyst_output = {}
    item.normalizer_attempt = 0

    client = MagicMock()
    client.chat.return_value = "mychar01, full shot, front view, wearing a coat, standing, neutral expression, soft daylight, village yard."

    session = MagicMock()

    normalizer.run(item, session, client, trigger_token="mychar01", lora_type="character")
    assert client.chat.called


def test_llm_pass_checker_run_accepts_lora_type() -> None:
    """llm_pass_checker.run must accept lora_type kwarg without TypeError."""
    from caption_agent.pipeline import llm_pass_checker

    item = MagicMock()
    item.normalized_caption = "mychar01, full shot, front view, wearing a coat, standing, neutral expression, soft daylight, village yard."
    item.batch = MagicMock()
    item.batch.source_type.value = "synthetic"
    item.batch.branch.value = "identity"
    item.raw_analyst_output = {}
    item.warnings = None

    client = MagicMock()
    client.chat.return_value = "[]"

    session = MagicMock()

    llm_pass_checker.run(item, session, client, trigger_token="mychar01", lora_type="character")
    assert client.chat.called


def test_rule_checker_accepts_lora_type() -> None:
    """rule_checker.check must accept lora_type kwarg without TypeError."""
    from caption_agent.pipeline import rule_checker
    from caption_agent.models.enums import BranchType, SourceType

    warnings = rule_checker.check(
        "mychar01, full shot, front view, wearing a coat, standing, neutral expression, soft daylight, village yard.",
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
        trigger_token="mychar01",
        lora_type="character",
    )
    assert isinstance(warnings, list)


