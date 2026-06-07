"""Tests for configurable caption policy (D-114).

Covers:
- CaptionPolicyConfig defaults match expected constants
- get_project_policy null/custom fallback
- rule_checker policy parameterization and lora_type gating
- lora_type_guidance function
- load_prompt_with_policy rendering
- API endpoints (GET/PUT/DELETE /api/projects/{id}/policy)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from caption_agent.config.policy_defaults import (
    DEFAULT_IDENTITY_TRAIT_PATTERNS,
    DEFAULT_SETTING_OVERSPECIFIC_PHRASES,
    DEFAULT_SOURCE_REF_REQUIRED_SETTING,
)
from caption_agent.config.lora_type_guidance import get_lora_type_guidance
from caption_agent.models.enums import BranchType, SourceType
from caption_agent.pipeline import rule_checker
from caption_agent.pipeline._prompts import load_prompt_with_policy
from caption_agent.schemas.policy import CaptionPolicyConfig, get_project_policy


# ---------------------------------------------------------------------------
# CaptionPolicyConfig defaults
# ---------------------------------------------------------------------------

class TestCaptionPolicyConfigDefaults:
    def test_defaults_match_character_identity_patterns(self) -> None:
        p = CaptionPolicyConfig()
        assert p.identity_trait_patterns == DEFAULT_IDENTITY_TRAIT_PATTERNS

    def test_defaults_match_character_setting_phrases(self) -> None:
        p = CaptionPolicyConfig()
        assert p.setting_overspecific_phrases == DEFAULT_SETTING_OVERSPECIFIC_PHRASES

    def test_default_source_ref_setting(self) -> None:
        p = CaptionPolicyConfig()
        assert p.source_ref_required_setting == DEFAULT_SOURCE_REF_REQUIRED_SETTING

    def test_default_custom_rules_none(self) -> None:
        p = CaptionPolicyConfig()
        assert p.custom_normalizer_rules is None
        assert p.custom_checker_rules is None

    def test_extra_fields_ignored(self) -> None:
        """Old stored JSON with extra keys must not crash (backward compat)."""
        p = CaptionPolicyConfig.model_validate({"identity_trait_patterns": [], "unknown_future_field": "x"})
        assert p.identity_trait_patterns == []


# ---------------------------------------------------------------------------
# get_project_policy
# ---------------------------------------------------------------------------

class TestGetProjectPolicy:
    def _project(self, caption_policy=None) -> MagicMock:
        m = MagicMock()
        m.caption_policy = caption_policy
        return m

    def test_null_policy_returns_defaults(self) -> None:
        project = self._project(None)
        p = get_project_policy(project)
        assert p.identity_trait_patterns == DEFAULT_IDENTITY_TRAIT_PATTERNS

    def test_custom_policy_overrides_defaults(self) -> None:
        project = self._project({
            "identity_trait_patterns": ["custom pattern"],
            "setting_overspecific_phrases": ["custom phrase"],
        })
        p = get_project_policy(project)
        assert p.identity_trait_patterns == ["custom pattern"]
        assert p.setting_overspecific_phrases == ["custom phrase"]
        # Unset fields still use defaults
        assert p.source_ref_required_setting == DEFAULT_SOURCE_REF_REQUIRED_SETTING

    def test_custom_policy_with_custom_rules(self) -> None:
        project = self._project({"custom_normalizer_rules": "MY RULE"})
        p = get_project_policy(project)
        assert p.custom_normalizer_rules == "MY RULE"


# ---------------------------------------------------------------------------
# rule_checker — policy parameterization
# ---------------------------------------------------------------------------

_GOOD_CAPTION = (
    "mychar01, medium shot, front view, wearing a coat, standing, "
    "neutral expression, soft daylight, indoor setting"
)


class TestRuleCheckerPolicyParam:
    def test_defaults_fire_on_identity_phrase(self) -> None:
        caption = _GOOD_CAPTION + ", gray eyes clearly visible"
        warnings = rule_checker.check(caption, trigger_token="mychar01")
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" in codes

    def test_custom_patterns_fire_on_custom_phrase(self) -> None:
        policy = CaptionPolicyConfig(
            identity_trait_patterns=[r"unique blue eyes"],
            setting_overspecific_phrases=[],
        )
        caption = _GOOD_CAPTION + ", unique blue eyes"
        warnings = rule_checker.check(caption, trigger_token="mychar01", policy=policy)
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" in codes

    def test_custom_patterns_dont_fire_on_default_phrase(self) -> None:
        """Custom patterns replace project defaults; default phrases must not trigger."""
        policy = CaptionPolicyConfig(
            identity_trait_patterns=[r"unique blue eyes"],
            setting_overspecific_phrases=[],
        )
        caption = _GOOD_CAPTION + ", gray eyes clearly visible"
        warnings = rule_checker.check(caption, trigger_token="mychar01", policy=policy)
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" not in codes

    def test_empty_identity_patterns_no_overcaption(self) -> None:
        policy = CaptionPolicyConfig(identity_trait_patterns=[], setting_overspecific_phrases=[])
        caption = _GOOD_CAPTION + ", gray eyes clearly visible"
        warnings = rule_checker.check(caption, trigger_token="mychar01", policy=policy)
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" not in codes

    def test_custom_setting_phrase_fires(self) -> None:
        policy = CaptionPolicyConfig(
            identity_trait_patterns=[],
            setting_overspecific_phrases=["neon-lit alley"],
        )
        caption = _GOOD_CAPTION.replace("indoor setting", "neon-lit alley setting")
        warnings = rule_checker.check(caption, trigger_token="mychar01", policy=policy)
        codes = [w["code"] for w in warnings]
        assert "SETTING_OVERSPECIFIC" in codes

    def test_setting_phrase_fires_by_default(self) -> None:
        caption = _GOOD_CAPTION.replace("indoor setting", "wooden building background")
        warnings = rule_checker.check(caption, trigger_token="mychar01")
        codes = [w["code"] for w in warnings]
        assert "SETTING_OVERSPECIFIC" in codes

    def test_custom_source_ref_setting_fires(self) -> None:
        policy = CaptionPolicyConfig(
            identity_trait_patterns=[],
            setting_overspecific_phrases=[],
            source_ref_required_setting="white seamless background",
        )
        # Caption uses default "gray studio background" — should fail custom check
        ref_caption = (
            "mychar01, head-and-shoulders portrait, front view, "
            "bare shoulders visible, neutral expression, gray studio background"
        )
        warnings = rule_checker.check(
            ref_caption,
            source_type=SourceType.REFERENCE,
            trigger_token="mychar01",
            policy=policy,
        )
        codes = [w["code"] for w in warnings]
        assert "SOURCE_REF_PATTERN_VIOLATION" in codes


# ---------------------------------------------------------------------------
# rule_checker — lora_type gating (D-114)
# ---------------------------------------------------------------------------

class TestRuleCheckerLoraTypeGating:
    def test_style_lora_skips_identity_overcaption(self) -> None:
        caption = _GOOD_CAPTION + ", gray eyes clearly visible"
        warnings = rule_checker.check(caption, trigger_token="mychar01", lora_type="style")
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" not in codes

    def test_object_lora_skips_identity_overcaption(self) -> None:
        caption = _GOOD_CAPTION + ", distinctive nose"
        warnings = rule_checker.check(caption, trigger_token="mychar01", lora_type="object")
        codes = [w["code"] for w in warnings]
        assert "IDENTITY_OVERCAPTION" not in codes

    def test_style_lora_skips_source_ref_pattern_violation(self) -> None:
        # A reference-type caption without "gray studio background" must NOT fire for style loras.
        ref_caption = (
            "mychar01, head-and-shoulders portrait, front view, "
            "bare shoulders visible, neutral expression, white wall"
        )
        warnings = rule_checker.check(
            ref_caption,
            source_type=SourceType.REFERENCE,
            trigger_token="mychar01",
            lora_type="style",
        )
        codes = [w["code"] for w in warnings]
        assert "SOURCE_REF_PATTERN_VIOLATION" not in codes

    def test_style_lora_skips_adult_branch_mismatch(self) -> None:
        analyst = {"adult_context": True, "other_characters": []}
        warnings = rule_checker.check(
            _GOOD_CAPTION,
            trigger_token="mychar01",
            lora_type="style",
            branch=BranchType.IDENTITY,
            analyst_output=analyst,
        )
        codes = [w["code"] for w in warnings]
        assert "ADULT_BRANCH_MISMATCH" not in codes

    def test_character_lora_still_fires_adult_branch_mismatch(self) -> None:
        analyst = {"adult_context": True, "other_characters": []}
        warnings = rule_checker.check(
            _GOOD_CAPTION,
            trigger_token="mychar01",
            lora_type="character",
            branch=BranchType.IDENTITY,
            analyst_output=analyst,
        )
        codes = [w["code"] for w in warnings]
        assert "ADULT_BRANCH_MISMATCH" in codes


# ---------------------------------------------------------------------------
# lora_type_guidance
# ---------------------------------------------------------------------------

class TestLoraTypeGuidance:
    def test_character_guidance_non_empty(self) -> None:
        g = get_lora_type_guidance("character")
        assert len(g) > 10
        assert "character" in g.lower()

    def test_style_guidance_non_empty(self) -> None:
        g = get_lora_type_guidance("style")
        assert len(g) > 10
        assert "style" in g.lower()

    def test_all_lora_types_have_guidance(self) -> None:
        for lt in ("character", "creature", "style", "clothing", "pose", "object", "face"):
            assert get_lora_type_guidance(lt), f"Empty guidance for {lt}"

    def test_unknown_type_falls_back_to_character(self) -> None:
        g = get_lora_type_guidance("totally_unknown_type")
        assert g == get_lora_type_guidance("character")


# ---------------------------------------------------------------------------
# load_prompt_with_policy
# ---------------------------------------------------------------------------

class TestLoadPromptWithPolicy:
    def test_defaults_inject_identity_patterns_into_normalizer(self) -> None:
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", policy=None)
        # The identity_trait_note block should include default identity patterns.
        assert "gray eyes" in rendered
        assert "ordinary body build" in rendered

    def test_custom_policy_identity_patterns_in_normalizer(self) -> None:
        policy = CaptionPolicyConfig(
            identity_trait_patterns=["sapphire_eye_color", "custom_nose_shape"],
            setting_overspecific_phrases=[],
        )
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", policy=policy)
        assert "sapphire_eye_color" in rendered
        assert "custom_nose_shape" in rendered
        # Default patterns should NOT appear (replaced by custom ones)
        assert "gray eyes" not in rendered

    def test_style_lora_has_empty_identity_note_in_normalizer(self) -> None:
        rendered = load_prompt_with_policy(
            "normalizer_system.txt", "mychar01", lora_type="style", policy=None
        )
        # For style, identity_trait_note is empty — default patterns must not appear
        assert "gray eyes" not in rendered
        # But the lora_type_guidance for style should be there
        assert "style" in rendered.lower()

    def test_custom_normalizer_rules_appended(self) -> None:
        policy = CaptionPolicyConfig(custom_normalizer_rules="SPECIAL PROJECT RULE XYZ")
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", policy=policy)
        assert "SPECIAL PROJECT RULE XYZ" in rendered

    def test_no_custom_rules_when_none(self) -> None:
        policy = CaptionPolicyConfig(custom_normalizer_rules=None)
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", policy=policy)
        assert "Additional project rules" not in rendered

    def test_trigger_token_substituted(self) -> None:
        rendered = load_prompt_with_policy("normalizer_system.txt", "my_trigger", policy=None)
        assert "my_trigger" in rendered

    def test_checker_custom_rules_use_checker_rules_field(self) -> None:
        policy = CaptionPolicyConfig(
            custom_normalizer_rules="NORMALIZER RULE",
            custom_checker_rules="CHECKER RULE",
        )
        checker_rendered = load_prompt_with_policy(
            "checker_system.txt", "mychar01", policy=policy, use_checker_rules=True
        )
        assert "CHECKER RULE" in checker_rendered
        assert "NORMALIZER RULE" not in checker_rendered

    def test_setting_overspecific_note_in_normalizer(self) -> None:
        """Default setting phrases should appear in the setting_overspecific_note block."""
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", policy=None)
        assert "wooden building" in rendered

    def test_lora_type_guidance_in_normalizer(self) -> None:
        rendered = load_prompt_with_policy("normalizer_system.txt", "mychar01", lora_type="character")
        # The character guidance block should appear
        assert get_lora_type_guidance("character") in rendered


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_with_project():
    """FastAPI TestClient with an in-memory DB and a test project."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from caption_agent.api import deps as _deps
    from caption_agent.main import app
    from caption_agent.models import Base, Project
    from caption_agent.orchestration.queue import BatchQueue
    from caption_agent.storage.session import get_session

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = SessionLocal()

    def _override():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_session] = _override
    _deps.set_queue(BatchQueue())

    c = TestClient(app, raise_server_exceptions=True)

    # Create a test project
    r = c.post("/api/projects", json={"name": "policy_test_project", "trigger_token": "t3st"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    yield c, project_id

    app.dependency_overrides.clear()
    db_session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


class TestPolicyAPI:
    def test_get_policy_returns_defaults_for_new_project(self, client_with_project) -> None:
        c, pid = client_with_project
        r = c.get(f"/api/projects/{pid}/policy")
        assert r.status_code == 200
        data = r.json()
        assert data["identity_trait_patterns"] == DEFAULT_IDENTITY_TRAIT_PATTERNS
        assert data["source_ref_required_setting"] == DEFAULT_SOURCE_REF_REQUIRED_SETTING

    def test_put_policy_updates_and_get_returns_updated(self, client_with_project) -> None:
        c, pid = client_with_project
        payload = {
            "identity_trait_patterns": ["custom_eye"],
            "setting_overspecific_phrases": ["neon alley"],
            "source_ref_required_setting": "white background",
            "coarse_setting_note": "keep it vague",
            "custom_normalizer_rules": None,
            "custom_checker_rules": None,
        }
        r = c.put(f"/api/projects/{pid}/policy", json=payload)
        assert r.status_code == 200

        r2 = c.get(f"/api/projects/{pid}/policy")
        assert r2.status_code == 200
        data = r2.json()
        assert data["identity_trait_patterns"] == ["custom_eye"]
        assert data["source_ref_required_setting"] == "white background"

    def test_delete_policy_resets_to_defaults(self, client_with_project) -> None:
        c, pid = client_with_project
        # First set a custom policy
        c.put(f"/api/projects/{pid}/policy", json={
            "identity_trait_patterns": ["custom"],
            "setting_overspecific_phrases": [],
            "source_ref_required_setting": "x",
            "coarse_setting_note": "y",
            "custom_normalizer_rules": None,
            "custom_checker_rules": None,
        })

        # Reset
        r = c.delete(f"/api/projects/{pid}/policy")
        assert r.status_code == 200
        data = r.json()
        assert data["identity_trait_patterns"] == DEFAULT_IDENTITY_TRAIT_PATTERNS

        # Confirm DB is null → GET also returns defaults
        r2 = c.get(f"/api/projects/{pid}/policy")
        assert r2.json()["identity_trait_patterns"] == DEFAULT_IDENTITY_TRAIT_PATTERNS

    def test_get_policy_404_on_missing_project(self, client_with_project) -> None:
        c, _ = client_with_project
        r = c.get("/api/projects/99999/policy")
        assert r.status_code == 404
