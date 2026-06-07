"""Unit tests for the rule checker (caption_agent/pipeline/rule_checker.py).

Pure-logic tests — no DB, no LLM, no mocking needed.
"""

from __future__ import annotations

import pytest

from caption_agent.models.enums import BranchType, SourceType
from caption_agent.pipeline.rule_checker import check


# ---- Helpers ----

def _codes(warnings: list[dict]) -> set[str]:
    return {w["code"] for w in warnings}


_GOOD_SYNTHETIC = (
    "p3rs0n4, head-and-shoulders portrait, front view, wearing a simple 1980s shirt, "
    "neutral expression, soft daylight, rural Russian village interior"
)

_GOOD_REFERENCE = (
    "p3rs0n4, fullbody pose, front view, wearing only underwear, neutral expression, "
    "gray studio background"
)


# ---- Passing captions ----

def test_good_synthetic_caption_no_warnings() -> None:
    warnings = check(_GOOD_SYNTHETIC, source_type=SourceType.SYNTHETIC)
    assert warnings == []


def test_good_reference_caption_no_warnings() -> None:
    warnings = check(_GOOD_REFERENCE, source_type=SourceType.REFERENCE)
    assert warnings == []


def test_portrait_bare_shoulders_passes_clothing_check() -> None:
    caption = (
        "p3rs0n4, head-and-shoulders portrait, front view, bare shoulders visible, "
        "neutral expression, soft daylight, village interior"
    )
    codes = _codes(check(caption))
    assert "CLOTHING_MISSING" not in codes


def test_clothing_not_in_frame_passes() -> None:
    caption = (
        "p3rs0n4, upper-torso portrait, left three-quarter view, clothing not in frame, "
        "slight smile, natural window light, village yard"
    )
    codes = _codes(check(caption))
    assert "CLOTHING_MISSING" not in codes


# ---- TRIGGER_MISSING ----

def test_trigger_missing() -> None:
    caption = "portrait, front view, wearing a shirt, neutral expression, soft daylight, village"
    codes = _codes(check(caption))
    assert "TRIGGER_MISSING" in codes


def test_trigger_present_but_not_first() -> None:
    caption = "front view, p3rs0n4, wearing a shirt, neutral expression, soft daylight, village"
    codes = _codes(check(caption))
    assert "TRIGGER_MISSING" in codes


# ---- AGE_PHRASE ----

def test_age_phrase_young_adult_man() -> None:
    caption = "p3rs0n4, young adult man, portrait, wearing a shirt, neutral, daylight, village"
    codes = _codes(check(caption))
    assert "AGE_PHRASE" in codes


def test_age_phrase_young_man() -> None:
    caption = "p3rs0n4, young man, portrait, wearing a shirt, neutral, daylight, village"
    codes = _codes(check(caption))
    assert "AGE_PHRASE" in codes


def test_no_age_phrase_if_not_present() -> None:
    codes = _codes(check(_GOOD_SYNTHETIC))
    assert "AGE_PHRASE" not in codes


# ---- SLOT_MISSING (D-099: structural check replaces CLOTHING/SETTING/LIGHTING_MISSING) ----

def test_slot_missing_no_clothing_indicator() -> None:
    caption = (
        "p3rs0n4, head-and-shoulders portrait, front view, "
        "neutral expression, soft daylight, village interior"
    )
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "SLOT_MISSING" in codes


def test_slot_missing_too_few_tokens() -> None:
    """Caption with far too few tokens triggers SLOT_MISSING."""
    caption = "p3rs0n4, medium shot, front view, wearing a shirt"
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "SLOT_MISSING" in codes


def test_slot_missing_not_raised_on_complete_caption() -> None:
    caption = (
        "p3rs0n4, medium shot, front view, wearing a T-shirt, "
        "standing, neutral expression, soft daylight, village yard"
    )
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "SLOT_MISSING" not in codes


def test_slot_missing_any_setting_word_valid() -> None:
    """Open-vocabulary settings like 'riverbank', 'lunar surface' must not cause SLOT_MISSING."""
    for setting in ("riverbank", "lunar surface", "ocean floor", "neon-lit alley", "spaceship deck"):
        caption = (
            f"p3rs0n4, medium shot, front view, wearing a jacket, "
            f"standing, neutral expression, soft daylight, {setting}"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "SLOT_MISSING" not in codes, f"False positive for setting: {setting!r}"


def test_slot_missing_any_lighting_word_valid() -> None:
    """Open-vocabulary lighting like 'blue neon glow', 'ring light' must not cause SLOT_MISSING."""
    for lighting in ("blue neon glow", "ring light", "red stage lighting", "bioluminescent light"):
        caption = (
            f"p3rs0n4, medium shot, front view, wearing a jacket, "
            f"standing, neutral expression, {lighting}, urban street"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "SLOT_MISSING" not in codes, f"False positive for lighting: {lighting!r}"


def test_slot_missing_not_checked_for_reference() -> None:
    codes = _codes(check(_GOOD_REFERENCE, source_type=SourceType.REFERENCE))
    assert "SLOT_MISSING" not in codes


# ---- STYLE_TOKEN ----

def test_style_token_photorealistic() -> None:
    caption = (
        "p3rs0n4, photorealistic head-and-shoulders portrait, front view, "
        "wearing a shirt, neutral, daylight, village"
    )
    codes = _codes(check(caption))
    assert "STYLE_TOKEN" in codes


def test_style_token_cinematic() -> None:
    caption = "p3rs0n4, cinematic portrait, wearing a shirt, neutral, daylight, village"
    codes = _codes(check(caption))
    assert "STYLE_TOKEN" in codes


def test_no_style_token_in_good_caption() -> None:
    codes = _codes(check(_GOOD_SYNTHETIC))
    assert "STYLE_TOKEN" not in codes


# ---- NEGATIVE_WORDING ----

def test_negative_wording_no_nose_hump() -> None:
    caption = "p3rs0n4, portrait, front view, wearing a shirt, no nose hump, daylight, village"
    codes = _codes(check(caption))
    assert "NEGATIVE_WORDING" in codes


# ---- IDENTITY_OVERCAPTION ----

def test_identity_overcaption_gray_eyes() -> None:
    caption = (
        "p3rs0n4, portrait, front view, wearing a shirt, gray eyes clearly visible, "
        "neutral, daylight, village"
    )
    codes = _codes(check(caption))
    assert "IDENTITY_OVERCAPTION" in codes


def test_identity_overcaption_same_nose() -> None:
    caption = "p3rs0n4, portrait, wearing a shirt, same nose shape, neutral, daylight, village"
    codes = _codes(check(caption))
    assert "IDENTITY_OVERCAPTION" in codes


# ---- NUDE_ON_CROPPED_PORTRAIT ----

def test_nude_on_portrait_identity_branch() -> None:
    caption = "p3rs0n4, head-and-shoulders portrait, front view, nude, neutral, daylight, village"
    analyst = {"crop": "portrait (head and shoulders)"}
    codes = _codes(check(caption, branch=BranchType.IDENTITY, analyst_output=analyst))
    assert "NUDE_ON_CROPPED_PORTRAIT" in codes


def test_nude_on_fullbody_identity_branch_no_violation() -> None:
    caption = (
        "p3rs0n4, fullbody pose, front view, nude, neutral expression, soft daylight, "
        "forest river"
    )
    analyst = {"crop": "fullbody"}
    codes = _codes(check(caption, branch=BranchType.IDENTITY, analyst_output=analyst))
    assert "NUDE_ON_CROPPED_PORTRAIT" not in codes


# ---- ADULT_BRANCH_MISMATCH ----

def test_adult_context_in_identity_branch_triggers_mismatch() -> None:
    codes = _codes(check(
        _GOOD_SYNTHETIC,
        branch=BranchType.IDENTITY,
        analyst_output={"adult_context": True},
    ))
    assert "ADULT_BRANCH_MISMATCH" in codes


def test_adult_context_in_adult_branch_no_mismatch() -> None:
    codes = _codes(check(
        _GOOD_SYNTHETIC,
        branch=BranchType.ADULT_AROUSED,
        analyst_output={"adult_context": True},
    ))
    assert "ADULT_BRANCH_MISMATCH" not in codes


# ---- MULTI_CHARACTER ----

def test_multi_character_detected() -> None:
    codes = _codes(check(
        _GOOD_SYNTHETIC,
        analyst_output={"other_characters": ["person in background"]},
    ))
    assert "MULTI_CHARACTER" in codes


def test_no_multi_character_when_alone() -> None:
    codes = _codes(check(_GOOD_SYNTHETIC, analyst_output={"other_characters": []}))
    assert "MULTI_CHARACTER" not in codes


def test_multi_character_sentinel_early_exit() -> None:
    """MULTI_CHARACTER sentinel from normalizer → only one warning, no cascade."""
    sentinel = "MULTI_CHARACTER: review required before training use"
    warnings = check(sentinel)
    assert len(warnings) == 1
    assert warnings[0]["code"] == "MULTI_CHARACTER"


def test_multi_character_sentinel_case_insensitive() -> None:
    warnings = check("multi_character: something")
    assert len(warnings) == 1
    assert warnings[0]["code"] == "MULTI_CHARACTER"


# ---- SOURCE_REF_PATTERN_VIOLATION ----

def test_source_ref_missing_gray_studio_background() -> None:
    caption = (
        "p3rs0n4, fullbody pose, front view, wearing only underwear, neutral expression, "
        "forest background"
    )
    codes = _codes(check(caption, source_type=SourceType.REFERENCE))
    assert "SOURCE_REF_PATTERN_VIOLATION" in codes


def test_source_ref_with_lighting_token_is_violation() -> None:
    caption = (
        "p3rs0n4, head-and-shoulders portrait, front view, bare shoulders visible, "
        "neutral expression, soft daylight, gray studio background"
    )
    codes = _codes(check(caption, source_type=SourceType.REFERENCE))
    assert "SOURCE_REF_PATTERN_VIOLATION" in codes


def test_source_ref_correct_pattern_no_violation() -> None:
    codes = _codes(check(_GOOD_REFERENCE, source_type=SourceType.REFERENCE))
    assert "SOURCE_REF_PATTERN_VIOLATION" not in codes


# ---- SETTING_OVERSPECIFIC (D-074) — still in rule_checker via regex ----
# Note: SETTING_MISSING and LIGHTING_MISSING were removed in D-099 (open-vocabulary).
# Open-slot presence is now handled by SLOT_MISSING (structural count).


# SETTING_OVERSPECIFIC was removed from rule_checker in D-099 (now LLM checker only).
# LIGHTING_MISSING was removed in D-099 (open-vocabulary, now covered by SLOT_MISSING structurally).


# ---- FRAMING_INVALID / VIEW_INVALID (D-098) ----

def test_framing_invalid_on_non_canonical_token() -> None:
    caption = (
        "p3rs0n4, bust shot, front view, wearing a shirt, "
        "standing, neutral expression, soft daylight, village yard"
    )
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "FRAMING_INVALID" in codes


def test_framing_valid_canonical_tokens() -> None:
    for framing in (
        "extreme close-up", "close-up", "head-and-shoulders portrait",
        "upper-torso portrait", "medium shot", "cowboy shot",
        "three-quarter shot", "full shot", "fullbody", "wide shot",
    ):
        caption = (
            f"p3rs0n4, {framing}, front view, wearing a shirt, "
            "standing, neutral expression, soft daylight, village yard"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "FRAMING_INVALID" not in codes, framing


def test_framing_valid_with_close_modifier() -> None:
    caption = (
        "p3rs0n4, close head-and-shoulders portrait, front view, wearing a shirt, "
        "standing, neutral expression, soft daylight, village yard"
    )
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "FRAMING_INVALID" not in codes


def test_view_invalid_on_non_canonical_synonym() -> None:
    for bad_view in ("left side profile", "side profile", "three-quarter left view"):
        caption = (
            f"p3rs0n4, head-and-shoulders portrait, {bad_view}, wearing a shirt, "
            "standing, neutral expression, soft daylight, village yard"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "VIEW_INVALID" in codes, bad_view


def test_view_valid_direction_tokens() -> None:
    for view in (
        "front view", "left three-quarter view", "right three-quarter view",
        "left profile", "right profile", "left three-quarter back view",
        "right three-quarter back view", "back view",
    ):
        caption = (
            f"p3rs0n4, medium shot, {view}, wearing a shirt, "
            "standing, neutral expression, soft daylight, village yard"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "VIEW_INVALID" not in codes, view


def test_view_valid_standalone_angles() -> None:
    for view in ("bird's eye view", "top-down view", "worm's eye view"):
        caption = (
            f"p3rs0n4, full shot, {view}, wearing a shirt, "
            "standing, neutral expression, soft daylight, rooftop"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "VIEW_INVALID" not in codes, view


def test_view_valid_direction_with_height_modifier() -> None:
    for combined in (
        "front view, low angle",
        "left three-quarter view, high angle",
        "right profile, dutch angle",
    ):
        caption = (
            f"p3rs0n4, medium shot, {combined}, wearing a shirt, "
            "standing, neutral expression, soft daylight, village yard"
        )
        codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
        assert "VIEW_INVALID" not in codes, combined


def test_view_invalid_height_modifier_alone() -> None:
    """Height modifier alone without direction is not valid."""
    caption = (
        "p3rs0n4, medium shot, high angle, wearing a shirt, "
        "standing, neutral expression, soft daylight, village yard"
    )
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "VIEW_INVALID" in codes


def test_framing_view_checks_apply_to_reference() -> None:
    codes = _codes(check(_GOOD_REFERENCE, source_type=SourceType.REFERENCE))
    assert "FRAMING_INVALID" not in codes
    assert "VIEW_INVALID" not in codes


# ---- Multiple violations at once ----

def test_multiple_violations_returned_together() -> None:
    caption = "portrait, wearing something"  # no trigger, bad framing, bad view
    codes = _codes(check(caption, source_type=SourceType.SYNTHETIC))
    assert "TRIGGER_MISSING" in codes
    assert "FRAMING_INVALID" in codes
    assert "VIEW_INVALID" in codes
