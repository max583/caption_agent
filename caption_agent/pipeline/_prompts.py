"""Prompt template loader for pipeline modules.

Templates live in ``caption_agent/prompts/`` and are loaded at call-time so that
edits to .txt files take effect without reinstalling the package.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas.policy import CaptionPolicyConfig

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _resolve_prompt_filename(base: str, lora_type: str) -> str:
    """Return type-specific prompt filename if it exists, else fall back to base.

    Convention (D-115): typed file = ``{stem}_{lora_type}.{ext}``
    Example: for lora_type="style", tries "normalizer_system_style.txt" first,
    falls back to "normalizer_system.txt" when not found.
    Character lora_type always uses the base file — no character-specific variant is created.
    """
    stem, ext = base.rsplit(".", 1)
    typed = f"{stem}_{lora_type}.{ext}"
    if (_PROMPTS_DIR / typed).exists():
        return typed
    return base


def load_prompt(filename: str) -> str:
    """Load a prompt template by filename from the prompts directory."""
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt_with_trigger(filename: str, trigger_token: str) -> str:
    """Load a prompt template and substitute the ``{trigger_token}`` placeholder.

    Uses simple string replacement (not .format()) so other curly-brace-like
    constructs in the template are not affected.
    """
    return load_prompt(filename).replace("{trigger_token}", trigger_token)


def load_prompt_with_context(
    filename: str,
    trigger_token: str,
    lora_type: str = "character",
) -> str:
    """Load a prompt template and substitute ``{trigger_token}``, ``{lora_type}``,
    and ``{lora_type_guidance}``.

    D-109 Track B: ``{lora_type_guidance}`` is substituted with type-specific guidance
    text from ``get_lora_type_guidance()``.
    """
    from caption_agent.config.lora_type_guidance import get_lora_type_guidance  # noqa: PLC0415

    return (
        load_prompt(_resolve_prompt_filename(filename, lora_type))
        .replace("{trigger_token}", trigger_token)
        .replace("{lora_type}", lora_type)
        .replace("{lora_type_guidance}", get_lora_type_guidance(lora_type))
    )


def load_prompt_with_policy(
    filename: str,
    trigger_token: str,
    lora_type: str = "character",
    policy: "CaptionPolicyConfig | None" = None,
    *,
    use_checker_rules: bool = False,
) -> str:
    """Load a prompt template and fill all context placeholders from policy + lora_type.

    Substitutes:
      {trigger_token}             — the project trigger token
      {lora_type}                 — lora type string value
      {lora_type_guidance}        — D-109 Track B type-specific guidance prose
      {identity_trait_note}       — pattern list for character loras; empty for others
      {setting_overspecific_note} — list of forbidden background phrases; or empty
      {custom_rules}              — optional project-specific extra rules block; or empty

    Args:
        use_checker_rules: when True, uses ``policy.custom_checker_rules`` instead of
            ``policy.custom_normalizer_rules`` for the ``{custom_rules}`` placeholder.
            Pass True when loading the checker prompt.
    """
    from caption_agent.config.lora_type_guidance import get_lora_type_guidance  # noqa: PLC0415
    from caption_agent.schemas.policy import CaptionPolicyConfig  # noqa: PLC0415

    p = policy or CaptionPolicyConfig()

    # {identity_trait_note} — pattern list for character loras, empty for others.
    if lora_type == "character" and p.identity_trait_patterns:
        lines = "\n".join(f"  - {pat}" for pat in p.identity_trait_patterns)
        identity_note = (
            "Do NOT describe these stable identity traits of the character:\n" + lines
        )
    else:
        identity_note = ""

    # {setting_overspecific_note} — forbidden phrase list, or empty.
    if p.setting_overspecific_phrases:
        phrase_list = ", ".join(f'"{ph}"' for ph in p.setting_overspecific_phrases)
        setting_note = f"Forbidden specific background phrases: {phrase_list}."
    else:
        setting_note = ""

    # {custom_rules} — optional extra rules block.
    if use_checker_rules:
        custom_text = (p.custom_checker_rules or "").strip()
    else:
        custom_text = (p.custom_normalizer_rules or "").strip()
    custom_block = f"\n\n## Additional project rules\n\n{custom_text}" if custom_text else ""

    return (
        load_prompt(_resolve_prompt_filename(filename, lora_type))
        .replace("{trigger_token}", trigger_token)
        .replace("{lora_type}", lora_type)
        .replace("{lora_type_guidance}", get_lora_type_guidance(lora_type))
        .replace("{identity_trait_note}", identity_note)
        .replace("{setting_overspecific_note}", setting_note)
        .replace("{custom_rules}", custom_block)
    )
