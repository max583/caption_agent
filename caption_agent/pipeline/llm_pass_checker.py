"""Pipeline Step 5: LLM Pass Checker (LLM text call).

Semantic + policy validation of the normalized caption. Catches subtle violations
that the regex-based RuleChecker misses (e.g., implicit age phrases, framing/nudity
conflicts, inaccurate descriptions).

Saves result to ``ImageItem.llm_pass_result`` and merges any new warnings into
``ImageItem.warnings``.

Raises ``LLMValidationError`` if the LLM response cannot be parsed as a JSON array.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from ..llm.client import LLMClient, LLMValidationError
from ..logging_setup.system_logger import get_system_logger
from ..models import ImageItem
from ..models.enums import BranchType, SourceType
from ..schemas.policy import CaptionPolicyConfig
from ._prompts import load_prompt_with_policy


def run(
    item: ImageItem,
    session: Session,  # noqa: ARG001
    client: LLMClient,
    *,
    temperature: float | None = None,
    trigger_token: str = "p3rs0n4",
    lora_type: str = "character",
    policy: CaptionPolicyConfig | None = None,
) -> None:
    """Run LLM semantic check; update ``item.llm_pass_result`` and ``item.warnings``."""
    system_prompt = load_prompt_with_policy(
        "checker_system.txt", trigger_token, lora_type, policy, use_checker_rules=True
    )
    user_text = _build_user_text(item)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    log = get_system_logger()
    log.debug("[llm_pass_checker] item %d — checking caption", item.id)

    raw = client.chat(messages, temperature=temperature)
    new_warnings = _parse_response(raw)

    result: dict[str, Any] = {
        "ok": len(new_warnings) == 0,
        "warnings": new_warnings,
        "raw_response": raw,
    }
    item.llm_pass_result = result

    if log.isEnabledFor(logging.DEBUG):
        if new_warnings:
            codes = [w.get("code", "?") for w in new_warnings]
            log.debug("[llm_pass_checker] item %d — %d warning(s): %s", item.id, len(new_warnings), codes)
        else:
            log.debug("[llm_pass_checker] item %d — OK, no warnings", item.id)

    # Merge LLM-checker warnings into the item's combined warnings list.
    existing = list(item.warnings or [])
    for w in new_warnings:
        w_copy = dict(w)
        w_copy["source"] = "llm_pass_checker"
        existing.append(w_copy)
    item.warnings = existing or None


def _build_user_text(item: ImageItem) -> str:
    batch = item.batch
    source_type: str = (batch.source_type.value if batch else SourceType.SYNTHETIC.value)
    branch: str = (batch.branch.value if batch else BranchType.IDENTITY.value)

    analyst = item.raw_analyst_output or {}
    parts: list[str] = []
    parts.append(f"caption: {item.normalized_caption or ''}")
    parts.append(f"source_type: {source_type}")
    parts.append(f"branch: {branch}")

    if analyst:
        relevant = {k: analyst[k] for k in (
            "crop", "camera_angle", "clothing", "expression", "setting",
            "other_characters", "adult_context",
        ) if k in analyst}
        parts.append(f"analyst_fields: {json.dumps(relevant, ensure_ascii=False)}")

    return "\n".join(parts)


def _parse_response(raw: str) -> list[dict[str, Any]]:
    """Parse the checker response as a JSON array of warning objects."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("` \n")
    # Handle empty / explicit "no issues" response.
    if not cleaned or cleaned.lower() in ("[]", "no issues", "no violations"):
        return []
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [w for w in data if isinstance(w, dict)]
        raise LLMValidationError(f"Checker returned non-array JSON: {cleaned[:200]!r}")
    except json.JSONDecodeError as exc:
        raise LLMValidationError(f"Checker response is not valid JSON: {exc}") from exc
