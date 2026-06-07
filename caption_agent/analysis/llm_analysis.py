"""LLM recommendation pass for dataset analysis — D-108a.

Called once per analysis request (no tool-calling, per D-089).
Returns a list of recommendation dicts, or None on any failure.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from ..config.schema import LLMConfig
from ..llm.client import LLMClient, is_thinking_model
from ..models.batch import Batch
from ..models.enums import ItemState
from ..models.image_item import ImageItem
from ..pipeline._prompts import load_prompt
from .dataset_stats import ProjectStats

# ---------------------------------------------------------------------------
# Per-type guidance injected into the system prompt ({lora_type_guidance}).
# ---------------------------------------------------------------------------

_LORA_TYPE_GUIDANCE: dict[str, str] = {
    "character": (
        "Face and body consistency alongside pose variety. "
        "Portrait-only datasets prevent pose generalisation — fullbody and medium shots are essential. "
        "Binding risk: a single expression, setting, or outfit repeated too often will leak into every generation."
    ),
    "creature": (
        "Body structure coverage from multiple angles and scales. "
        "Avoid setting binding (e.g. all images on the same background). "
        "Include close-up detail shots of distinctive features."
    ),
    "style": (
        "Diversity of subjects, compositions, and lighting is critical — "
        "style must generalise across varied content, not just one subject type."
    ),
    "clothing": (
        "Multiple viewing angles of the garment (front, back, 3/4, detail shots). "
        "Vary lighting, body position, and background to isolate the garment from context."
    ),
    "pose": (
        "Full-body framing throughout — no cropped portraits. "
        "Multiple subjects or models prevent face binding. "
        "Check that the pose is the only consistent element across images."
    ),
    "object": (
        "Multiple viewing angles (front, side, 3/4, close detail). "
        "Vary backgrounds and lighting. "
        "Avoid setting or context binding."
    ),
    "face": (
        "Close-up and near-close-up framing only. "
        "Multiple expressions and lighting directions. "
        "Avoid background or expression binding."
    ),
}

_CAPTION_SAMPLE_SIZE = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_captions(project_id: int, session: Session) -> list[str]:
    batch_ids = [
        row.id
        for row in session.query(Batch.id).filter(Batch.project_id == project_id).all()
    ]
    if not batch_ids:
        return []
    items = (
        session.query(ImageItem)
        .filter(
            ImageItem.batch_id.in_(batch_ids),
            ImageItem.state.in_([ItemState.APPROVED, ItemState.AWAITING_REVIEW]),
        )
        .order_by(ImageItem.id)
        .limit(_CAPTION_SAMPLE_SIZE)
        .all()
    )
    return [
        text
        for item in items
        if (text := (item.final_caption or item.normalized_caption))
    ]


def _stats_to_text(stats: ProjectStats) -> str:
    lines = [
        f"total_items: {stats.total_items}",
        f"approved: {stats.approved_count}",
        f"awaiting_review: {stats.awaiting_review_count}",
        f"source_type_split: {json.dumps(stats.source_type_split, ensure_ascii=False)}",
    ]
    for f, dist in stats.distributions.items():
        lines.append(f"{f}: {json.dumps(dist, ensure_ascii=False)}")
    if stats.warning_codes:
        lines.append(f"warning_codes: {json.dumps(stats.warning_codes, ensure_ascii=False)}")
    return "\n".join(lines)


def _parse_recommendations(raw: str) -> list[dict[str, Any]] | None:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("` \n")
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    recs = data.get("recommendations")
    if not isinstance(recs, list):
        return None
    return recs[:5]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_dataset_llm_analysis(
    *,
    project_id: int,
    lora_type: str,
    stats: ProjectStats,
    session: Session,
    llm_cfg: LLMConfig,
) -> list[dict[str, Any]] | None:
    """Call the LLM once and return ≤5 recommendation dicts, or None on any failure."""
    if stats.total_items == 0:
        return None

    guidance = _LORA_TYPE_GUIDANCE.get(lora_type, _LORA_TYPE_GUIDANCE["character"])
    system_prompt = (
        load_prompt("dataset_analysis_system.txt")
        .replace("{lora_type}", lora_type)
        .replace("{lora_type_guidance}", guidance)
    )

    captions = _sample_captions(project_id, session)
    caption_block = (
        "\n".join(f"- {c}" for c in captions) if captions else "(no captions available)"
    )

    user_text = (
        "=== DATASET STATISTICS ===\n"
        + _stats_to_text(stats)
        + "\n\n=== CAPTION SAMPLE ===\n"
        + caption_block
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    # Thinking models (qwen3, deepseek-r1, …) burn token budget on internal CoT —
    # passing 0 omits max_tokens from the payload entirely (see client.py), letting
    # the model use its own default.
    max_tokens = 0 if is_thinking_model(llm_cfg.model_id) else 512

    with LLMClient(llm_cfg) as client:
        raw = client.chat(messages, max_tokens=max_tokens)

    return _parse_recommendations(raw)
