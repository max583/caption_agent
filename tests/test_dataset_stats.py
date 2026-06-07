"""Tests for compute_project_stats — D-118 type-aware analytics."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from caption_agent.analysis.dataset_stats import (
    TYPE_DISTRIBUTION_FIELDS,
    compute_project_stats,
)
from caption_agent.models import Batch, ImageItem, Project
from caption_agent.models.enums import ItemState, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(session: Session, lora_type: str = "character") -> Project:
    project = Project(name="test-project", lora_type=lora_type)
    session.add(project)
    session.flush()
    return project


def _make_batch(session: Session, project_id: int) -> Batch:
    batch = Batch(
        project_id=project_id,
        name="batch-1",
        source_folder_path="/tmp/x",
        source_type=SourceType.SYNTHETIC,
    )
    session.add(batch)
    session.flush()
    return batch


def _make_item(
    session: Session,
    batch_id: int,
    state: ItemState = ItemState.APPROVED,
    raw_analyst_output: dict | None = None,
    final_caption: str | None = None,
) -> ImageItem:
    item = ImageItem(
        batch_id=batch_id,
        file_path="/tmp/img.jpg",
        file_name="img.jpg",
        state=state,
        raw_analyst_output=raw_analyst_output,
        final_caption=final_caption,
    )
    session.add(item)
    session.flush()
    return item


# ---------------------------------------------------------------------------
# Basic smoke
# ---------------------------------------------------------------------------


def test_empty_project_returns_zero_totals(session: Session) -> None:
    project = _make_project(session)
    stats = compute_project_stats(project.id, session)
    assert stats.total_items == 0
    assert stats.approved_count == 0
    assert stats.awaiting_review_count == 0
    assert stats.distributions == {}
    assert stats.per_batch == []


# ---------------------------------------------------------------------------
# character type (default)
# ---------------------------------------------------------------------------


def test_character_distributions_keys(session: Session) -> None:
    project = _make_project(session, lora_type="character")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={
            "crop": "bust shot",
            "camera_angle": "eye level",
            "pose": "standing",
            "expression": "neutral",
            "clothing": "wearing a blue jacket",
        },
    )
    stats = compute_project_stats(project.id, session, lora_type="character")

    # character fields + clothing classification
    expected_keys = set(TYPE_DISTRIBUTION_FIELDS["character"]) | {"clothing"}
    assert set(stats.distributions.keys()) == expected_keys
    assert stats.total_items == 1
    assert stats.approved_count == 1


def test_character_clothing_classification(session: Session) -> None:
    project = _make_project(session, lora_type="character")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={"clothing": "wearing a hoodie and jeans"},
    )
    stats = compute_project_stats(project.id, session, lora_type="character")
    assert stats.distributions["clothing"].get("clothed", 0) == 1


def test_character_clothing_nude_classification(session: Session) -> None:
    project = _make_project(session, lora_type="character")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={"clothing": "nude"},
    )
    stats = compute_project_stats(project.id, session, lora_type="character")
    assert stats.distributions["clothing"].get("nude", 0) == 1


def test_missing_analyst_output_yields_unknown(session: Session) -> None:
    project = _make_project(session, lora_type="character")
    batch = _make_batch(session, project.id)
    _make_item(session, batch.id, raw_analyst_output=None)
    stats = compute_project_stats(project.id, session, lora_type="character")
    for key in TYPE_DISTRIBUTION_FIELDS["character"]:
        assert stats.distributions[key].get("unknown", 0) == 1


# ---------------------------------------------------------------------------
# style type
# ---------------------------------------------------------------------------


def test_style_distribution_keys(session: Session) -> None:
    project = _make_project(session, lora_type="style")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={
            "style_descriptor": "impressionist",
            "medium_technique": "oil painting",
            "lighting_mood": "warm golden",
        },
    )
    stats = compute_project_stats(project.id, session, lora_type="style")

    assert set(stats.distributions.keys()) == {"style_descriptor", "medium_technique", "lighting_mood"}
    assert stats.distributions["style_descriptor"].get("impressionist", 0) == 1
    assert stats.distributions["medium_technique"].get("oil painting", 0) == 1
    assert stats.distributions["lighting_mood"].get("warm golden", 0) == 1


def test_style_has_no_clothing_key(session: Session) -> None:
    project = _make_project(session, lora_type="style")
    batch = _make_batch(session, project.id)
    _make_item(session, batch.id, raw_analyst_output={"style_descriptor": "minimalist"})
    stats = compute_project_stats(project.id, session, lora_type="style")
    assert "clothing" not in stats.distributions
    assert "framing" not in stats.distributions
    assert "view" not in stats.distributions


# ---------------------------------------------------------------------------
# clothing type
# ---------------------------------------------------------------------------


def test_clothing_distribution_keys(session: Session) -> None:
    project = _make_project(session, lora_type="clothing")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={
            "garment_type": "jacket",
            "cut_silhouette": "oversized",
            "material": "denim",
            "how_worn": "open over shirt",
        },
    )
    stats = compute_project_stats(project.id, session, lora_type="clothing")

    assert set(stats.distributions.keys()) == {"garment_type", "cut_silhouette", "material", "how_worn"}
    assert stats.distributions["garment_type"].get("jacket", 0) == 1
    assert stats.distributions["material"].get("denim", 0) == 1


# ---------------------------------------------------------------------------
# per_batch distributions
# ---------------------------------------------------------------------------


def test_per_batch_distributions_match_project(session: Session) -> None:
    project = _make_project(session, lora_type="style")
    batch = _make_batch(session, project.id)
    _make_item(
        session,
        batch.id,
        raw_analyst_output={"style_descriptor": "impressionist", "medium_technique": "oil", "lighting_mood": "warm"},
    )
    stats = compute_project_stats(project.id, session, lora_type="style")

    assert len(stats.per_batch) == 1
    b = stats.per_batch[0]
    assert set(b.distributions.keys()) == {"style_descriptor", "medium_technique", "lighting_mood"}
    assert b.distributions["style_descriptor"] == stats.distributions["style_descriptor"]


# ---------------------------------------------------------------------------
# awaiting_review items are included
# ---------------------------------------------------------------------------


def test_awaiting_review_items_included(session: Session) -> None:
    project = _make_project(session)
    batch = _make_batch(session, project.id)
    _make_item(session, batch.id, state=ItemState.AWAITING_REVIEW)
    stats = compute_project_stats(project.id, session)
    assert stats.total_items == 1
    assert stats.awaiting_review_count == 1
    assert stats.approved_count == 0


# ---------------------------------------------------------------------------
# fallback for unknown lora_type uses character fields
# ---------------------------------------------------------------------------


def test_unknown_lora_type_falls_back_to_character(session: Session) -> None:
    project = _make_project(session, lora_type="character")
    batch = _make_batch(session, project.id)
    _make_item(session, batch.id, raw_analyst_output={"crop": "full body"})
    stats = compute_project_stats(project.id, session, lora_type="nonexistent_type")
    # Should have character fields
    for key in TYPE_DISTRIBUTION_FIELDS["character"]:
        assert key in stats.distributions
