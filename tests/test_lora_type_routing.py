"""Tests for Phase 9A: lora_type-based prompt routing and rule_checker gating (D-115).

Covers:
- _resolve_prompt_filename fallback to base when no typed file exists
- _resolve_prompt_filename returns typed filename when the file exists
- rule_checker._SKIPPED_CHECKS_BY_TYPE: character fires all gated checks
- rule_checker._SKIPPED_CHECKS_BY_TYPE: style skips STYLE_TOKEN, FRAMING_INVALID (passes them through)
- rule_checker._SKIPPED_CHECKS_BY_TYPE: unknown lora_type defaults to character behaviour
"""

from __future__ import annotations

import pytest

# Import from caption_agent.config first — this initialises the config package (and transitively
# caption_agent.schemas) in the correct order, avoiding the circular-import that occurs when
# schemas is initialised before config.  Same import order as test_caption_policy.py.
from caption_agent.config.lora_type_guidance import get_lora_type_guidance as _  # noqa: F401

from caption_agent.models.enums import BranchType, SourceType
from caption_agent.pipeline import rule_checker
from caption_agent.pipeline._prompts import _resolve_prompt_filename, _PROMPTS_DIR


# ---------------------------------------------------------------------------
# _resolve_prompt_filename routing (D-115)
# ---------------------------------------------------------------------------


class TestResolvePromptFilename:
    def test_fallback_when_no_typed_file_exists(self) -> None:
        """For a lora_type with no typed file, the base filename is returned unchanged.
        Uses lora_type='vehicle' — a type outside the project enum that will never have
        typed prompt files. All 7 supported types (character/style/face/clothing/creature/
        pose/object) now have typed files after Phase 9F."""
        result = _resolve_prompt_filename("normalizer_system.txt", "vehicle")
        assert result == "normalizer_system.txt"

    def test_returns_typed_filename_when_file_exists(self, tmp_path: pytest.FixtureValue, monkeypatch: pytest.MonkeyPatch) -> None:
        """When a type-specific file is present, _resolve_prompt_filename returns its name."""
        # Create a dummy typed prompt file in a temp dir.
        typed_file = tmp_path / "normalizer_system_style.txt"
        typed_file.write_text("style prompt content", encoding="utf-8")

        # Redirect _PROMPTS_DIR to tmp_path so the resolver finds the typed file.
        monkeypatch.setattr(
            "caption_agent.pipeline._prompts._PROMPTS_DIR", tmp_path
        )

        result = _resolve_prompt_filename("normalizer_system.txt", "style")
        assert result == "normalizer_system_style.txt"

    def test_character_always_falls_back_to_base(self) -> None:
        """character lora always uses the base file — no character-specific variant exists."""
        result = _resolve_prompt_filename("normalizer_system.txt", "character")
        assert result == "normalizer_system.txt"


# ---------------------------------------------------------------------------
# _SKIPPED_CHECKS_BY_TYPE gating in rule_checker (D-115)
# ---------------------------------------------------------------------------

# A structurally valid character caption — passes all checks except those we deliberately trigger.
_TRIGGER = "mychar01"
_BASE_CAPTION = (
    "mychar01, medium shot, front view, wearing a coat, standing, "
    "neutral expression, soft daylight, indoor setting"
)


class TestSkippedChecksCharacter:
    """character lora_type: all three historically-gated checks must still fire."""

    def test_all_three_gated_checks_fire_for_character(self) -> None:
        # Caption with an identity trait ("gray eyes") AND on REFERENCE source without
        # the required "gray studio background" AND analyst sees adult content on identity branch.
        caption = _BASE_CAPTION + ", gray eyes visible"
        analyst = {"adult_context": True, "other_characters": []}

        warnings = rule_checker.check(
            caption,
            source_type=SourceType.REFERENCE,
            branch=BranchType.IDENTITY,
            analyst_output=analyst,
            trigger_token=_TRIGGER,
            lora_type="character",
        )
        codes = {w["code"] for w in warnings}

        assert "IDENTITY_OVERCAPTION" in codes, "IDENTITY_OVERCAPTION must fire for character"
        assert "SOURCE_REF_PATTERN_VIOLATION" in codes, "SOURCE_REF_PATTERN_VIOLATION must fire for character"
        assert "ADULT_BRANCH_MISMATCH" in codes, "ADULT_BRANCH_MISMATCH must fire for character"


class TestSkippedChecksStyle:
    """style lora_type: style-token / framing / view checks must be silently skipped."""

    def test_style_token_skipped_for_style_lora(self) -> None:
        # "photorealistic" would trigger STYLE_TOKEN for character — must be silent for style.
        caption = "artnouveau_s, photorealistic illustration, warm palette, front view"
        warnings = rule_checker.check(caption, trigger_token="artnouveau_s", lora_type="style")
        codes = {w["code"] for w in warnings}
        assert "STYLE_TOKEN" not in codes

    def test_framing_invalid_skipped_for_style_lora(self) -> None:
        # No framing token — would produce FRAMING_INVALID for character.
        caption = "artnouveau_s, oil painting, warm palette, botanical illustration"
        warnings = rule_checker.check(caption, trigger_token="artnouveau_s", lora_type="style")
        codes = {w["code"] for w in warnings}
        assert "FRAMING_INVALID" not in codes

    def test_view_invalid_skipped_for_style_lora(self) -> None:
        # No view token — would produce VIEW_INVALID for character.
        caption = "artnouveau_s, oil painting, warm palette, botanical illustration"
        warnings = rule_checker.check(caption, trigger_token="artnouveau_s", lora_type="style")
        codes = {w["code"] for w in warnings}
        assert "VIEW_INVALID" not in codes

    def test_trigger_missing_still_fires_for_style_lora(self) -> None:
        # TRIGGER_MISSING is never skipped — universal check.
        caption = "photorealistic painting of a landscape, oil on canvas, muted colors"
        warnings = rule_checker.check(caption, trigger_token="artnouveau_s", lora_type="style")
        codes = {w["code"] for w in warnings}
        assert "TRIGGER_MISSING" in codes


class TestSkippedChecksUnknownType:
    """Unknown lora_type defaults to empty skip set (= character behaviour)."""

    def test_unknown_type_behaves_like_character(self) -> None:
        # With a fabricated lora_type, IDENTITY_OVERCAPTION should still fire
        # (unknown type → empty skip set → same as character).
        caption = _BASE_CAPTION + ", gray eyes visible"

        warnings = rule_checker.check(
            caption,
            trigger_token=_TRIGGER,
            lora_type="dragon_slayer",
        )
        codes = {w["code"] for w in warnings}
        assert "IDENTITY_OVERCAPTION" in codes, (
            "Unknown lora_type should default to character behaviour (all checks active)"
        )
