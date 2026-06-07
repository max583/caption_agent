"""Smoke tests for ORM models: create entities, verify relationships and cascade delete."""

from __future__ import annotations

from sqlalchemy.orm import Session

from caption_agent.models import (
    BatchStateHistory,
    BusinessLog,
    ImageItem,
    ImageItemErrorStats,
    Project,
    Batch,
)
from caption_agent.models.enums import (
    BatchState,
    BranchType,
    ItemState,
    LogLevel,
    SourceType,
)


def test_create_project(session: Session) -> None:
    project = Project(name="Test Project", description="desc")
    session.add(project)
    session.flush()
    assert project.id is not None
    assert project.default_source_type == SourceType.SYNTHETIC
    assert project.default_branch == BranchType.IDENTITY
    assert project.created_at is not None


def test_create_batch_with_project_relationship(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()

    batch = Batch(
        project_id=project.id,
        name="batch1",
        source_folder_path="/tmp/x",
    )
    session.add(batch)
    session.flush()
    assert batch.id is not None
    assert batch.project_id == project.id
    assert batch.state == BatchState.QUEUED
    assert batch.source_type == SourceType.SYNTHETIC
    # Backref.
    assert project.batches == [batch]


def test_image_item_belongs_to_batch(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()

    item = ImageItem(
        batch_id=batch.id,
        file_path="/x/img.png",
        file_name="img.png",
    )
    session.add(item)
    session.flush()
    assert item.state == ItemState.QUEUED
    assert item.normalizer_attempt == 0
    assert batch.image_items == [item]


def test_cascade_delete_project_removes_batches_and_items(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()
    item = ImageItem(batch_id=batch.id, file_path="/x/i.png", file_name="i.png")
    session.add(item)
    session.flush()

    project_id = project.id
    batch_id = batch.id
    item_id = item.id

    session.delete(project)
    session.flush()

    assert session.get(Project, project_id) is None
    assert session.get(Batch, batch_id) is None
    assert session.get(ImageItem, item_id) is None


def test_state_history_attaches_to_batch(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()

    history = BatchStateHistory(
        batch_id=batch.id,
        from_state=None,
        to_state=BatchState.QUEUED.value,
        reason="initial",
    )
    session.add(history)
    session.flush()
    assert batch.state_history == [history]


def test_error_stats_one_to_one(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()
    item = ImageItem(batch_id=batch.id, file_path="/x/i.png", file_name="i.png")
    session.add(item)
    session.flush()

    stats = ImageItemErrorStats(image_item_id=item.id, transient_count=2, policy_count=1)
    session.add(stats)
    session.flush()
    assert item.error_stats is stats
    assert stats.transient_count == 2


def test_business_log_basic(session: Session) -> None:
    project = Project(name="P1")
    session.add(project)
    session.flush()

    log = BusinessLog(
        event_type="project_created",
        message="Project P1 created",
        level=LogLevel.INFO,
        project_id=project.id,
    )
    session.add(log)
    session.flush()
    assert log.id is not None
    assert log.timestamp is not None


# ---------------------------------------------------------------------------
# Schema invariants: stable image identity + monotonic IDs
# ---------------------------------------------------------------------------

def test_image_item_unique_per_batch_and_path(session: Session) -> None:
    """(batch_id, file_path) is unique — re-adding the same file in a batch fails."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()

    session.add(ImageItem(batch_id=batch.id, file_path="/x/dup.png", file_name="dup.png"))
    session.flush()
    session.add(ImageItem(batch_id=batch.id, file_path="/x/dup.png", file_name="dup.png"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_image_item_same_path_allowed_in_different_batches(session: Session) -> None:
    """The uniqueness is per batch — the same file may appear in two batches."""
    project = Project(name="P1")
    session.add(project)
    session.flush()
    b1 = Batch(project_id=project.id, name="b1", source_folder_path="/x")
    b2 = Batch(project_id=project.id, name="b2", source_folder_path="/x")
    session.add_all([b1, b2])
    session.flush()

    session.add(ImageItem(batch_id=b1.id, file_path="/x/i.png", file_name="i.png"))
    session.add(ImageItem(batch_id=b2.id, file_path="/x/i.png", file_name="i.png"))
    session.flush()  # must not raise


def test_item_ids_not_reused_after_delete(session: Session) -> None:
    """AUTOINCREMENT: a deleted item's id is never handed to a new item.

    Regression for the stale-image bug: reused IDs made the browser serve a
    previous batch's cached image under /api/items/{id}/image.
    """
    project = Project(name="P1")
    session.add(project)
    session.flush()
    batch = Batch(project_id=project.id, name="b", source_folder_path="/x")
    session.add(batch)
    session.flush()

    it1 = ImageItem(batch_id=batch.id, file_path="/x/a.png", file_name="a.png")
    session.add(it1)
    session.flush()
    first_id = it1.id

    session.delete(it1)
    session.flush()

    it2 = ImageItem(batch_id=batch.id, file_path="/x/b.png", file_name="b.png")
    session.add(it2)
    session.flush()
    assert it2.id > first_id, "item id was reused after delete — AUTOINCREMENT not active"
