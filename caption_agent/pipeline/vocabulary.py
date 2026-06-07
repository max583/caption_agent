"""Controlled vocabulary — single source of truth for closed-set caption slots.

Both the rule checker (machine validation, ``rule_checker.py``) and the
normalizer LLM prompt (``prompts/normalizer_system.txt``) must use exactly these
tokens. The guide (``docs/research/caption_writing_guide.md``) documents them for
humans. When this list changes, update the prompt and the guide to match (D-098).

Framing and view vocabularies were expanded in D-098 to professional
cinematography/photography standards so the system works for any character or genre.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Framing / shot size — exactly one must appear in every caption.
# A leading modifier "close " is valid (e.g. "close head-and-shoulders portrait").
# "fullbody" is a legacy alias for "full shot" — accepted in existing captions.
# ---------------------------------------------------------------------------

FRAMING_TOKENS: tuple[str, ...] = (
    "extreme close-up",
    "close-up",
    "head-and-shoulders portrait",
    "upper-torso portrait",
    "medium shot",
    "cowboy shot",
    "three-quarter shot",
    "full shot",
    "fullbody",           # legacy alias — kept for backward compatibility
    "wide shot",
)

# ---------------------------------------------------------------------------
# View / camera angle — D-098 two-component system.
#
# A valid view is ONE of:
#   (a) A direction token (optionally combined with a height modifier), or
#   (b) A standalone angle token (bird's eye, top-down, worm's eye).
#
# Height modifiers alone are NOT valid without a direction or standalone angle.
# ---------------------------------------------------------------------------

# Direction (azimuth) — required unless a standalone angle is used.
VIEW_DIRECTION_TOKENS: tuple[str, ...] = (
    "front view",
    "left three-quarter view",
    "right three-quarter view",
    "left profile",
    "right profile",
    "left three-quarter back view",
    "right three-quarter back view",
    "back view",
)

# Height modifiers — optional, combine with a direction token.
VIEW_HEIGHT_TOKENS: tuple[str, ...] = (
    "high angle",
    "low angle",
    "dutch angle",
)

# Standalone angles — direction is implicit / not applicable.
VIEW_STANDALONE_TOKENS: tuple[str, ...] = (
    "bird's eye view",
    "top-down view",
    "worm's eye view",
)

# Convenience: all tokens whose presence satisfies the VIEW_INVALID check.
VIEW_TOKENS: tuple[str, ...] = VIEW_DIRECTION_TOKENS + VIEW_STANDALONE_TOKENS
