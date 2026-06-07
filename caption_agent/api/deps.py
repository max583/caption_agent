"""Shared FastAPI dependencies for API routers (Phase 3)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Batch, ImageItem, Project
from ..orchestration.queue import BatchQueue

# Module-level queue reference — set by main.py lifespan.
_queue_ref: BatchQueue | None = None


def set_queue(q: BatchQueue) -> None:
    """Called once from lifespan after the queue is created."""
    global _queue_ref
    _queue_ref = q


def get_queue() -> BatchQueue:
    """Return the live queue; raise 503 if not yet initialized."""
    if _queue_ref is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue not yet initialized",
        )
    return _queue_ref


def get_project_or_404(project_id: int, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


def get_batch_or_404(batch_id: int, session: Session) -> Batch:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return batch


def get_item_or_404(item_id: int, session: Session) -> ImageItem:
    item = session.get(ImageItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return item
