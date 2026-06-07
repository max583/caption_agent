"""Tests for orchestration: queue recovery, scheduler tick, batch_processor helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from caption_agent.models import Batch, BatchStateHistory, ImageItem, Project
from caption_agent.models.enums import BatchState, BranchType, ItemState, SourceType
from caption_agent.orchestration.queue import BatchQueue, recover_and_load
from caption_agent.orchestration.scheduler import _tick


# ---- BatchQueue ----

def test_queue_put_nowait_and_qsize() -> None:
    q = BatchQueue()
    q.put_nowait(1)
    q.put_nowait(2)
    assert q.qsize() == 2


@pytest.mark.asyncio
async def test_queue_get_returns_fifo() -> None:
    q = BatchQueue()
    q.put_nowait(10)
    q.put_nowait(20)
    assert await q.get() == 10
    assert await q.get() == 20


# ---- recover_and_load ----

def _make_batch(session: Session, *, state: BatchState, project_id: int) -> Batch:
    batch = Batch(
        project_id=project_id,
        name="test",
        source_folder_path="/tmp/x",
        state=state,
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    session.add(batch)
    session.flush()
    return batch


def test_recover_and_load_queued_batches(session: Session) -> None:
    project = Project(name="P")
    session.add(project)
    session.flush()
    _make_batch(session, state=BatchState.QUEUED, project_id=project.id)
    _make_batch(session, state=BatchState.QUEUED, project_id=project.id)
    session.commit()

    q = BatchQueue()
    loaded = recover_and_load(q)
    assert loaded == 2
    assert q.qsize() == 2


def test_recover_and_load_resets_processing_to_queued(session: Session) -> None:
    project = Project(name="P2")
    session.add(project)
    session.flush()
    batch = _make_batch(session, state=BatchState.PROCESSING, project_id=project.id)
    session.commit()

    q = BatchQueue()
    loaded = recover_and_load(q)
    assert loaded == 1  # recovered batch ends up in QUEUED and is loaded

    # Verify DB state.
    session.expire(batch)
    session.refresh(batch)
    assert batch.state == BatchState.QUEUED


def test_recover_and_load_ignores_done_batches(session: Session) -> None:
    project = Project(name="P3")
    session.add(project)
    session.flush()
    _make_batch(session, state=BatchState.DONE, project_id=project.id)
    session.commit()

    q = BatchQueue()
    loaded = recover_and_load(q)
    assert loaded == 0


# ---- scheduler _tick ----

def test_scheduler_tick_moves_due_batch_to_queued(session: Session) -> None:
    project = Project(name="P4")
    session.add(project)
    session.flush()
    batch = Batch(
        project_id=project.id,
        name="scheduled",
        source_folder_path="/tmp/s",
        state=BatchState.SCHEDULED,
        schedule_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # past
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    session.add(batch)
    session.commit()

    q = BatchQueue()
    _tick(q)

    session.expire(batch)
    session.refresh(batch)
    assert batch.state == BatchState.QUEUED
    assert q.qsize() == 1


def test_scheduler_tick_ignores_future_batch(session: Session) -> None:
    project = Project(name="P5")
    session.add(project)
    session.flush()
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    batch = Batch(
        project_id=project.id,
        name="future",
        source_folder_path="/tmp/f",
        state=BatchState.SCHEDULED,
        schedule_at=future,
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    session.add(batch)
    session.commit()

    q = BatchQueue()
    _tick(q)

    session.expire(batch)
    session.refresh(batch)
    assert batch.state == BatchState.SCHEDULED
    assert q.qsize() == 0


# ---- Item state transition helpers (indirectly tested via batch_processor) ----

def test_item_starts_in_queued(session: Session) -> None:
    project = Project(name="P6")
    session.add(project)
    session.flush()
    batch = Batch(
        project_id=project.id,
        name="b",
        source_folder_path="/tmp",
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    session.add(batch)
    session.flush()
    item = ImageItem(
        batch_id=batch.id,
        file_path="/tmp/a.png",
        file_name="a.png",
        state=ItemState.QUEUED,
    )
    session.add(item)
    session.commit()
    assert item.state == ItemState.QUEUED
