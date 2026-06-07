"""Default caption policy values for a character identity LoRA (D-114).

These are the values that were hardcoded in rule_checker.py before Phase 7.
A project with caption_policy=NULL uses these automatically via get_project_policy().
"""
from __future__ import annotations

DEFAULT_IDENTITY_TRAIT_PATTERNS: list[str] = [
    r"gray eyes(?: clearly visible)?",
    r"ordinary body build",
    r"same nose(?: shape)?",
    r"same chin",
    r"same hair colou?r",
    r"consistent dark hair",
    r"sharp facial features",
    r"distinctive nose",
    r"prominent chin",
    r"regular body",
]

DEFAULT_SETTING_OVERSPECIFIC_PHRASES: list[str] = [
    "wooden building", "wood panel wall", "wood paneling",
    "horizontal siding", "vertical siding",
    "log wall", "log cabin",
    "blurred green foliage", "blurred background foliage",
    "blurred trees", "blurred green background",
    "weathered fence", "weathered structure",
    "in front of a weathered",
]

DEFAULT_SOURCE_REF_REQUIRED_SETTING = "gray studio background"

DEFAULT_COARSE_SETTING_NOTE = (
    "Name the kind of place in 2–4 words — do not name specific recurring objects, materials,\n"
    "or architectural details. Examples: \"indoor setting\", \"urban outdoor setting\", "
    "\"outdoor setting\".\n"
    "Setting is coarse because over-specific recurring backgrounds bind to the trigger token "
    "across the dataset (D-074)."
)
