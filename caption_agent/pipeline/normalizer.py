"""Pipeline Step 3: Caption Normalizer (LLM text call).

Writes a policy-compliant training caption from the analyst output, provenance,
and active caption policy (D-073/D-074/D-077/D-084/D-085/D-086).

Saves result to ``ImageItem.normalized_caption``.
Raises ``LLMValidationError`` when the response is suspiciously malformed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..llm.client import LLMClient, LLMValidationError
from ..logging_setup.system_logger import get_system_logger
from ..models import ImageItem
from ..models.enums import SourceType
from ..schemas.policy import CaptionPolicyConfig
from ._prompts import load_prompt_with_policy

_MAX_ANALYST_CHARS = 1200


def run(
    item: ImageItem,
    session: Session,
    client: LLMClient,
    *,
    temperature: float | None = None,
    feedback: list[dict[str, str]] | None = None,
    trigger_token: str = "p3rs0n4",
    lora_type: str = "character",
    policy: CaptionPolicyConfig | None = None,
) -> None:
    """Generate a normalized caption; update ``item.normalized_caption`` in-place.

    Args:
        feedback: warnings from the previous rule-check iteration (self-retry loop).
    """
    batch = item.batch
    source_type: SourceType = batch.source_type if batch else SourceType.SYNTHETIC
    branch_name: str = batch.branch.value if batch else "identity"

    system_prompt = load_prompt_with_policy("normalizer_system.txt", trigger_token, lora_type, policy)
    user_text = _build_user_text(item, source_type=source_type, branch=branch_name, feedback=feedback)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    log = get_system_logger()
    attempt = getattr(item, "normalizer_attempt", 0)
    if log.isEnabledFor(logging.DEBUG):
        feedback_codes = [w.get("code", "?") for w in (feedback or [])]
        log.debug(
            "[normalizer] item %d attempt %d — feedback codes: %s",
            item.id, attempt, feedback_codes or "none",
        )

    raw = client.chat(messages, temperature=temperature)
    caption = _parse_response(raw)
    item.normalized_caption = caption

    if log.isEnabledFor(logging.DEBUG):
        preview = caption[:120].replace("\n", " ")
        log.debug(
            "[normalizer] item %d attempt %d — caption: %s%s",
            item.id, attempt, preview, "…" if len(caption) > 120 else "",
        )


def _build_user_text(
    item: ImageItem,
    *,
    source_type: SourceType,
    branch: str,
    feedback: list[dict[str, str]] | None,
) -> str:
    parts: list[str] = []

    parts.append("## Batch context")
    parts.append(f"source_type: {source_type.value}")
    parts.append(f"branch: {branch}")
    parts.append("caption_schema: v002_identity")

    analyst = item.raw_analyst_output or {}
    if analyst:
        parts.append("\n## Analyst output")
        parts.append(_summarize_analyst(analyst))

    if feedback:
        parts.append(f"\n## Previous attempt feedback (retry {item.normalizer_attempt})")
        for w in feedback:
            parts.append(f"- [{w.get('code', '?')}] {w.get('message', '')}")
        parts.append(
            "\nFix the issues listed above in your new caption. Do not introduce new violations."
        )

    parts.append("\nWrite the caption following the system prompt rules. Return only the caption text.")
    return "\n".join(parts)


def _summarize_analyst(analyst: dict[str, Any]) -> str:
    """Return a compact text representation of analyst fields for the normalizer prompt."""
    fields = [
        ("crop", analyst.get("crop")),
        ("camera_angle", analyst.get("camera_angle")),
        ("pose", analyst.get("pose")),
        ("clothing", analyst.get("clothing")),
        ("expression", analyst.get("expression")),
        ("setting", analyst.get("setting")),
        ("other_characters", analyst.get("other_characters")),
        ("adult_context", analyst.get("adult_context")),
        ("defects", analyst.get("defects")),
    ]
    lines = []
    for key, val in fields:
        if val is not None and val != [] and val != "":
            if isinstance(val, (list, dict)):
                lines.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
            else:
                lines.append(f"{key}: {val}")
    raw_desc = analyst.get("raw_description", "")
    if raw_desc:
        snippet = raw_desc[:_MAX_ANALYST_CHARS]
        lines.append(f"raw_description: {snippet}")
    return "\n".join(lines)


def _parse_response(raw: str) -> str:
    """Validate and clean the normalizer response."""
    caption = raw.strip().strip('"').strip("'")
    # Reject clearly non-caption responses (empty, multi-line JSON, etc.).
    if not caption:
        raise LLMValidationError("Normalizer returned an empty caption.")
    if caption.startswith("{") or caption.startswith("["):
        raise LLMValidationError(f"Normalizer returned JSON instead of caption: {caption[:200]!r}")
    # Reject multi-line responses (caption must be one line per guide).
    lines = [l for l in caption.splitlines() if l.strip()]
    if len(lines) > 3:
        raise LLMValidationError(
            f"Normalizer returned too many lines ({len(lines)}); expected a single-line caption."
        )
    return lines[0] if lines else caption
