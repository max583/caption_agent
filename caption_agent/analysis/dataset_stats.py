"""Dataset statistics pass — D-108, D-118.

Pure Python, no LLM calls. Computes slot distributions across APPROVED +
AWAITING_REVIEW items in a project, using raw_analyst_output fields selected
by lora_type (D-118 — type-aware analytics).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..models.batch import Batch
from ..models.enums import ItemState
from ..models.image_item import ImageItem

# ---------------------------------------------------------------------------
# Per-type distribution fields (D-118)
# ---------------------------------------------------------------------------

TYPE_DISTRIBUTION_FIELDS: dict[str, list[str]] = {
    "character": ["crop", "camera_angle", "pose", "expression"],
    "face":      ["crop", "camera_angle", "expression", "skin_tone", "facial_structure"],
    "pose":      ["crop", "camera_angle", "pose_action", "body_silhouette"],
    "style":     ["style_descriptor", "medium_technique", "lighting_mood"],
    "clothing":  ["garment_type", "cut_silhouette", "material", "how_worn"],
    "creature":  ["crop", "camera_angle", "creature_type", "pose"],
    "object":    ["object_type", "material", "form_shape", "surface_finish"],
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BatchStatsRow:
    batch_id: int
    batch_name: str
    source_type: str
    total: int
    distributions: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class ProjectStats:
    total_items: int
    approved_count: int
    awaiting_review_count: int
    distributions: dict[str, dict[str, int]]
    source_type_split: dict[str, int]
    warning_codes: dict[str, int]
    per_batch: list[BatchStatsRow]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _clothing_text_to_state(text: str) -> str:
    """Classify a free-text clothing description into a coarse state bucket."""
    lower = text.lower()
    if "underwear" in lower or "boxers" in lower or "briefs" in lower:
        return "underwear-only"
    if "bare shoulder" in lower or "bare-shoulder" in lower or "clothing not in frame" in lower:
        return "bare-shoulders"
    if "topless" in lower:
        return "topless"
    if "nude" in lower or "naked" in lower:
        return "nude"
    if any(kw in lower for kw in ("wearing", "shirt", "t-shirt", "jacket", "coat",
                                   "sweater", "hoodie", "trousers", "pants", "jeans",
                                   "clothed", "dressed")):
        return "clothed"
    return "other"


def _extract_distributions(
    items: list[ImageItem],
    fields: list[str],
    lora_type: str,
) -> dict[str, dict[str, int]]:
    """Aggregate raw_analyst_output values per field across all items.

    For character lora_type, the 'clothing' field is classified via
    _clothing_text_to_state rather than used verbatim.
    """
    result: dict[str, dict[str, int]] = {f: {} for f in fields}

    # character type also includes a 'clothing' distribution (classified)
    if lora_type == "character" and "clothing" not in result:
        result["clothing"] = {}

    for item in items:
        raw: dict | None = item.raw_analyst_output if isinstance(item.raw_analyst_output, dict) else None

        for f in fields:
            dist = result[f]
            value: str | None = raw.get(f) if raw is not None else None
            if not value or not isinstance(value, str):
                key = "unknown"
            else:
                key = value.strip().lower() or "unknown"
            dist[key] = dist.get(key, 0) + 1

        # clothing classification for character only
        if lora_type == "character":
            clothing_dist = result["clothing"]
            clothing_text: str | None = raw.get("clothing") if raw is not None else None
            if clothing_text and isinstance(clothing_text, str):
                key = _clothing_text_to_state(clothing_text)
            else:
                # Caption-text fallback
                caption = item.final_caption or item.normalized_caption or ""
                key = _clothing_text_to_state(caption) if caption else "unknown"
            clothing_dist[key] = clothing_dist.get(key, 0) + 1

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_INCLUDE_STATES: tuple[ItemState, ...] = (ItemState.APPROVED, ItemState.AWAITING_REVIEW)


def _inc(d: dict[str, int], key: str) -> None:
    d[key] = d.get(key, 0) + 1


def compute_project_stats(
    project_id: int,
    session: Session,
    *,
    lora_type: str = "character",
) -> ProjectStats:
    """Compute distribution stats for all APPROVED + AWAITING_REVIEW items in *project_id*."""
    fields = TYPE_DISTRIBUTION_FIELDS.get(lora_type, TYPE_DISTRIBUTION_FIELDS["character"])

    batches: list[Batch] = (
        session.query(Batch)
        .filter(Batch.project_id == project_id)
        .order_by(Batch.created_at)
        .all()
    )

    total = 0
    approved_count = 0
    awaiting_count = 0
    all_items: list[ImageItem] = []
    source_split: dict[str, int] = {}
    warn_agg: dict[str, int] = {}
    per_batch: list[BatchStatsRow] = []

    for batch in batches:
        items: list[ImageItem] = (
            session.query(ImageItem)
            .filter(
                ImageItem.batch_id == batch.id,
                ImageItem.state.in_(list(_INCLUDE_STATES)),
            )
            .all()
        )
        if not items:
            continue

        source_type_str = str(batch.source_type)

        for item in items:
            total += 1
            if item.state == ItemState.APPROVED:
                approved_count += 1
            else:
                awaiting_count += 1

            _inc(source_split, source_type_str)

            if item.warnings:
                for w in item.warnings:
                    code = w.get("code", "unknown") if isinstance(w, dict) else "unknown"
                    _inc(warn_agg, code)

        all_items.extend(items)

        b_distributions = _extract_distributions(items, fields, lora_type)
        per_batch.append(BatchStatsRow(
            batch_id=batch.id,
            batch_name=batch.name,
            source_type=source_type_str,
            total=len(items),
            distributions=b_distributions,
        ))

    project_distributions = (
        _extract_distributions(all_items, fields, lora_type) if all_items else {}
    )

    return ProjectStats(
        total_items=total,
        approved_count=approved_count,
        awaiting_review_count=awaiting_count,
        distributions=project_distributions,
        source_type_split=source_split,
        warning_codes=warn_agg,
        per_batch=per_batch,
    )
