"""Pipeline Step 4: Rule Checker (non-LLM).

Pure-Python validation against the caption policy. Returns a list of warning dicts.

Per D-087: no LLM call. Must run fast enough to be called on every normalizer iteration.
Per D-099: rule_checker owns ONLY closed-vocabulary and syntactic checks. Open-vocabulary
slot presence (lighting, setting, pose) is handled by the structural SLOT_MISSING check.
Per D-114: project-specific patterns (identity traits, setting phrases, source-ref setting)
are read from CaptionPolicyConfig at call time.
Per D-115: check gating is data-driven via _SKIPPED_CHECKS_BY_TYPE; unknown lora_type
values default to empty skip set (= character behaviour, all checks active).

Violation codes:
  TRIGGER_MISSING        — caption does not start with the trigger token
  AGE_PHRASE             — default age phrase present
  STYLE_TOKEN            — quality/style word present
  NEGATIVE_WORDING       — negative constraint present
  ADULT_BRANCH_MISMATCH  — sexual content on identity branch (gated by lora_type)
  MULTI_CHARACTER        — other people detected by analyst
  IDENTITY_OVERCAPTION   — stable identity trait named explicitly (gated by lora_type)
  NUDE_ON_CROPPED_PORTRAIT — nude on portrait crop (gated by lora_type)
  SOURCE_REF_PATTERN_VIOLATION — source ref doesn't match expected format (gated by lora_type)
  FRAMING_INVALID        — no canonical framing token (D-098, gated by lora_type)
  VIEW_INVALID           — no canonical view token (D-098, gated by lora_type)
  SLOT_MISSING           — structural: too few comma tokens or no clothing indicator (gated by lora_type)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ..models.enums import BranchType, SourceType
from .vocabulary import FRAMING_TOKENS, VIEW_DIRECTION_TOKENS, VIEW_STANDALONE_TOKENS

if TYPE_CHECKING:
    from ..schemas.policy import CaptionPolicyConfig


# ---- Compiled patterns (universal — not project-specific) ----

_STYLE_TOKENS = re.compile(
    r"\b(photorealistic|cinematic|handsome|beautiful|perfect skin|ultra[- ]?detailed|"
    r"masterpiece|8k|4k|high[- ]?fashion|model photoshoot|stunning|gorgeous)\b",
    re.IGNORECASE,
)

_AGE_PHRASES = re.compile(
    r"\b(young adult man|young man|young adult|teenage boy|teen|adolescent man)\b",
    re.IGNORECASE,
)

_NEGATIVE_WORDING = re.compile(
    r"\b(no |not |without |doesn't have |no visible |free of )(nose hump|brown eyes|modern clothing|"
    r"distorted|extra limbs|artifacts?|blur|noise|wrinkles?)",
    re.IGNORECASE,
)

_NUDE_WORDS = re.compile(r"\b(nude|naked|bare chest|bare torso)\b", re.IGNORECASE)

_PORTRAIT_CROPS = {"portrait", "head-and-shoulders", "upper-torso", "upper torso", "close crop"}

# Clothing/visibility indicators — syntactic markers, not open vocabulary.
_CLOTHING_INDICATORS = re.compile(
    r"\b(wearing |bare shoulders visible|bare neck visible|clothing not in frame|"
    r"clothing out of frame|in a |dressed in |in his |wearing only)\b",
    re.IGNORECASE,
)

# Lighting tokens that must NOT appear in source references (universal).
_LIGHTING_IN_SOURCE_REF = re.compile(
    r"\b(daylight|sunlight|window light|overcast|soft light|side light|"
    r"natural light|winter daylight|golden hour)\b",
    re.IGNORECASE,
)

# Framing / view — built from vocabulary.py (D-098).
_FRAMING_RE = re.compile(
    "|".join(re.escape(t) for t in FRAMING_TOKENS), re.IGNORECASE
)
_VIEW_DIRECTION_RE = re.compile(
    "|".join(re.escape(t) for t in VIEW_DIRECTION_TOKENS), re.IGNORECASE
)
_VIEW_STANDALONE_RE = re.compile(
    "|".join(re.escape(t) for t in VIEW_STANDALONE_TOKENS), re.IGNORECASE
)

# Minimum comma-separated parts for a structurally complete synthetic caption:
# trigger(1) + framing(1) + view(1–2) + 4 open slots = 7 minimum (conservative).
_MIN_SYNTHETIC_PARTS = 7

# Per D-115: which rule-checker codes to skip for each lora_type.
# Populated incrementally as type-specific prompt files are authored.
# Unknown lora_type values default to empty set (= character behaviour, all checks active).
# Note: CLOTHING_MISSING and CLOTHING_OVERDESCRIBED are LLM-checker codes; they are included
# here so the same dict can serve as the authoritative skip list for future LLM checker routing.
_SKIPPED_CHECKS_BY_TYPE: dict[str, set[str]] = {
    "character": set(),
    "style": {
        "IDENTITY_OVERCAPTION", "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH",
        "CLOTHING_MISSING", "CLOTHING_OVERDESCRIBED", "AGE_PHRASE",
        "NUDE_ON_CROPPED_PORTRAIT", "FRAMING_INVALID", "VIEW_INVALID",
        "SLOT_MISSING", "SETTING_OVERSPECIFIC", "STYLE_TOKEN",
    },
    "face": {
        "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH",
        "SLOT_MISSING", "SETTING_OVERSPECIFIC",
    },
    "clothing": {
        "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH", "AGE_PHRASE",
        "NUDE_ON_CROPPED_PORTRAIT", "IDENTITY_OVERCAPTION", "CLOTHING_OVERDESCRIBED",
    },
    "creature": {
        "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH",
        "CLOTHING_MISSING", "AGE_PHRASE", "NUDE_ON_CROPPED_PORTRAIT",
    },
    "pose": {
        "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH", "AGE_PHRASE",
        "NUDE_ON_CROPPED_PORTRAIT", "IDENTITY_OVERCAPTION",
        "CLOTHING_MISSING", "SETTING_OVERSPECIFIC",
    },
    "object": {
        "SOURCE_REF_PATTERN_VIOLATION", "ADULT_BRANCH_MISMATCH", "AGE_PHRASE",
        "NUDE_ON_CROPPED_PORTRAIT", "IDENTITY_OVERCAPTION",
        "CLOTHING_MISSING", "FRAMING_INVALID", "VIEW_INVALID",
    },
}


# ---- Public API ----

Warning = dict[str, str]


def check(
    caption: str,
    *,
    source_type: SourceType = SourceType.SYNTHETIC,
    branch: BranchType = BranchType.IDENTITY,
    analyst_output: dict[str, Any] | None = None,
    trigger_token: str = "p3rs0n4",
    lora_type: str = "character",
    policy: "CaptionPolicyConfig | None" = None,
) -> list[Warning]:
    """Run all rule checks; return a (possibly empty) list of warning dicts.

    Per D-114 / D-115: check behaviour is gated by _SKIPPED_CHECKS_BY_TYPE[lora_type].
    Unknown lora_type values default to "character" behaviour (empty skip set).
    Pattern lists and the source-ref setting token are read from policy (project defaults if None).
    """
    from ..schemas.policy import CaptionPolicyConfig  # noqa: PLC0415

    _policy = policy or CaptionPolicyConfig()
    _skipped = _SKIPPED_CHECKS_BY_TYPE.get(lora_type, set())

    # Build per-call regexes from policy (project defaults if policy is None).
    _identity_re: re.Pattern[str] | None = None
    if "IDENTITY_OVERCAPTION" not in _skipped and _policy.identity_trait_patterns:
        _identity_re = re.compile(
            "|".join(r"(?:" + p + r")" for p in _policy.identity_trait_patterns),
            re.IGNORECASE,
        )

    _src_ref_re = re.compile(
        re.escape(_policy.source_ref_required_setting), re.IGNORECASE
    )

    # Early exit: normalizer returned the MULTI_CHARACTER sentinel.
    if caption.strip().upper().startswith("MULTI_CHARACTER:"):
        return [{
            "code": "MULTI_CHARACTER",
            "message": "Multi-character image detected. Cannot be used for single-character "
                       "training without multi-character policy (D-080).",
        }]

    warnings: list[Warning] = []
    a = analyst_output or {}
    caption_lower = caption.lower()

    # 1. TRIGGER_MISSING
    if not caption_lower.startswith(trigger_token.lower()):
        warnings.append({
            "code": "TRIGGER_MISSING",
            "message": f'Caption must start with "{trigger_token}".',
        })

    # 2. AGE_PHRASE
    if "AGE_PHRASE" not in _skipped and _AGE_PHRASES.search(caption):
        warnings.append({
            "code": "AGE_PHRASE",
            "message": "Default age phrase found. Omit age unless image is a deliberate "
                       "age variant (D-077).",
        })

    # 3. STYLE_TOKEN
    if "STYLE_TOKEN" not in _skipped:
        match = _STYLE_TOKENS.search(caption)
        if match:
            warnings.append({
                "code": "STYLE_TOKEN",
                "message": f'Style/quality token "{match.group()}" found. Use concrete visual '
                           "descriptions instead (D-073).",
            })

    # 4. NEGATIVE_WORDING
    match = _NEGATIVE_WORDING.search(caption)
    if match:
        warnings.append({
            "code": "NEGATIVE_WORDING",
            "message": f'Negative constraint "{match.group()}" found. Describe what IS '
                       "present, not what is absent.",
        })

    # 5. ADULT_BRANCH_MISMATCH — gated by lora_type (D-114/D-115)
    if "ADULT_BRANCH_MISMATCH" not in _skipped and a.get("adult_context") and branch == BranchType.IDENTITY:
        warnings.append({
            "code": "ADULT_BRANCH_MISMATCH",
            "message": "Analyst detected adult/sexual content but branch is identity. "
                       "Route to adult_aroused branch (D-070).",
        })

    # 6. MULTI_CHARACTER (from analyst output)
    others = a.get("other_characters") or []
    if others:
        warnings.append({
            "code": "MULTI_CHARACTER",
            "message": "Other characters detected. Multi-character captioning policy not "
                       "yet defined (D-080).",
        })

    # 7. IDENTITY_OVERCAPTION — character lora only; patterns from policy (D-114)
    if _identity_re is not None:
        match = _identity_re.search(caption)
        if match:
            warnings.append({
                "code": "IDENTITY_OVERCAPTION",
                "message": f'Identity-invariant phrase "{match.group()}" found. Remove it — '
                           "traits bind via visual repetition (D-086).",
            })

    # 8. NUDE_ON_CROPPED_PORTRAIT — gated by lora_type (D-115)
    crop = str(a.get("crop", "")).lower()
    is_cropped = any(c in crop for c in _PORTRAIT_CROPS)
    if "NUDE_ON_CROPPED_PORTRAIT" not in _skipped and is_cropped and branch == BranchType.IDENTITY and _NUDE_WORDS.search(caption):
        warnings.append({
            "code": "NUDE_ON_CROPPED_PORTRAIT",
            "message": 'Use "bare shoulders visible" or "clothing not in frame" on portrait '
                       'crops. Do not write "nude"/"naked" (D-084).',
        })

    # 9. SOURCE_REF_PATTERN_VIOLATION — gated by lora_type (D-114/D-115)
    if "SOURCE_REF_PATTERN_VIOLATION" not in _skipped and source_type == SourceType.REFERENCE:
        if not _src_ref_re.search(caption):
            warnings.append({
                "code": "SOURCE_REF_PATTERN_VIOLATION",
                "message": f'Source reference caption must contain '
                           f'"{_policy.source_ref_required_setting}" (D-085).',
            })
        if _LIGHTING_IN_SOURCE_REF.search(caption):
            warnings.append({
                "code": "SOURCE_REF_PATTERN_VIOLATION",
                "message": "Source reference caption must not contain a lighting token — "
                           "studio lighting is uniform (D-085).",
            })

    # 10. FRAMING_INVALID — must use a canonical framing token (D-098); gated by lora_type (D-115)
    if "FRAMING_INVALID" not in _skipped and not _FRAMING_RE.search(caption):
        warnings.append({
            "code": "FRAMING_INVALID",
            "message": (
                "Caption must contain a canonical framing token: "
                + ", ".join(FRAMING_TOKENS)
                + " (D-098)."
            ),
        })

    # 11. VIEW_INVALID — must use a direction token OR a standalone angle token (D-098); gated by lora_type (D-115)
    if "VIEW_INVALID" not in _skipped and not (_VIEW_DIRECTION_RE.search(caption) or _VIEW_STANDALONE_RE.search(caption)):
        warnings.append({
            "code": "VIEW_INVALID",
            "message": (
                "Caption must contain a direction token ("
                + ", ".join(VIEW_DIRECTION_TOKENS)
                + ") or a standalone angle token ("
                + ", ".join(VIEW_STANDALONE_TOKENS)
                + "). Height modifiers (high angle, low angle, dutch angle) alone are not valid (D-098)."
            ),
        })

    # 12. SLOT_MISSING — structural check (D-099); gated by lora_type (D-115)
    if "SLOT_MISSING" not in _skipped and source_type == SourceType.SYNTHETIC:
        missing_slots: list[str] = []

        # 12a. Clothing/visibility indicator — syntactic pattern (not open vocabulary).
        if not _CLOTHING_INDICATORS.search(caption):
            missing_slots.append("clothing or visibility state")

        # 12b. Token count — a complete synthetic caption has ≥7 comma-separated parts.
        parts = [p.strip().rstrip(".") for p in caption.split(",") if p.strip().rstrip(".")]
        if len(parts) < _MIN_SYNTHETIC_PARTS:
            open_slots = max(0, len(parts) - 3)  # subtract trigger + framing + view
            if open_slots < 5:
                expected = ["pose", "expression", "lighting", "setting"]
                for slot in expected:
                    if slot not in missing_slots:
                        missing_slots.append(slot)

        if missing_slots:
            warnings.append({
                "code": "SLOT_MISSING",
                "message": (
                    f"Caption appears to be missing: {', '.join(missing_slots)}. "
                    "A complete synthetic caption needs: clothing/visibility, pose, "
                    "expression, lighting, setting (D-099)."
                ),
            })

    # 13. SETTING_OVERSPECIFIC — phrases from policy (D-114); gated by lora_type (D-115)
    if "SETTING_OVERSPECIFIC" not in _skipped and source_type == SourceType.SYNTHETIC and _policy.setting_overspecific_phrases:
        for phrase in _policy.setting_overspecific_phrases:
            if phrase.lower() in caption_lower:
                warnings.append({
                    "code": "SETTING_OVERSPECIFIC",
                    "message": (
                        f'Setting phrase "{phrase}" over-specifies the background. '
                        "Name the kind of place, not specific structures or textures (D-074)."
                    ),
                })
                break  # one warning per caption is enough

    return warnings
