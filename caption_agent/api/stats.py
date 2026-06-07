"""Aggregation helpers: compute batch and project stats from the DB.

These are called on every poll (every 15–30 s) so they stay as simple
COUNT queries rather than full ORM loads.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Batch, ImageItem, Project
from ..models.enums import BatchState, ItemState
from ..schemas.batches import BatchCard, BatchOut, BatchStateHistoryOut
from ..schemas.projects import ProjectCard, ProjectOut

_ACTIVE_STATES = {BatchState.PROCESSING, BatchState.QUEUED, BatchState.SCANNING}
_TERMINAL_ITEM_STATES = {
    ItemState.APPROVED,
    ItemState.DROPPED,
    ItemState.SKIPPED,
    ItemState.DONE,
    ItemState.ERROR,
}


def _batch_item_counts(batch_id: int, session: Session) -> dict[str, int]:
    rows = (
        session.query(ImageItem.state, func.count(ImageItem.id))
        .filter(ImageItem.batch_id == batch_id)
        .group_by(ImageItem.state)
        .all()
    )
    counts: dict[str, int] = {}
    for state, cnt in rows:
        counts[state] = cnt
    return counts


def _progress_pct(counts: dict[str, int]) -> int:
    total = sum(counts.values())
    if total == 0:
        return 0
    done = sum(
        counts.get(s, 0)
        for s in [
            ItemState.APPROVED,
            ItemState.DROPPED,
            ItemState.SKIPPED,
            ItemState.DONE,
            ItemState.AWAITING_REVIEW,
            ItemState.ERROR,
        ]
    )
    return min(100, int(done * 100 / total))


def _batch_status_category(batch: Batch) -> str:
    if batch.state == BatchState.ERROR:
        return "error"
    if batch.state == BatchState.AWAITING_REVIEW:
        return "review"
    if batch.state == BatchState.SCANNING:
        return "scanning"
    if batch.state in _ACTIVE_STATES:
        return "active"
    if batch.state == BatchState.SCHEDULED:
        return "scheduled"
    return "idle"


def _history_sort_key(h) -> datetime:
    """Sort key for state-history rows that tolerates mixed naive/aware datetimes.

    SQLite with DateTime(timezone=True) normally returns naive datetimes, but a
    stray timezone-aware value (e.g. from a manual edit) would otherwise make
    sorting raise "can't compare offset-naive and offset-aware datetimes".
    Normalize everything to naive UTC for comparison.
    """
    dt = h.changed_at
    if dt is None:
        return datetime.min
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def build_batch_out(batch: Batch, session: Session) -> BatchOut:
    counts = _batch_item_counts(batch.id, session)
    total = sum(counts.values())
    pct = _progress_pct(counts)
    history = [
        BatchStateHistoryOut.model_validate(h)
        for h in sorted(batch.state_history, key=_history_sort_key)
    ]
    out = BatchOut.model_validate(batch)
    out.total_items = total
    out.queued_items = counts.get(ItemState.QUEUED, 0)
    out.processing_items = sum(
        counts.get(s, 0)
        for s in [
            ItemState.READING_CONTEXT,
            ItemState.ANALYZING,
            ItemState.NORMALIZING,
            ItemState.RULE_CHECK,
            ItemState.LLM_PASS_CHECK,
            ItemState.REGENERATING,
        ]
    )
    out.awaiting_review_items = counts.get(ItemState.AWAITING_REVIEW, 0)
    out.approved_items = counts.get(ItemState.APPROVED, 0)
    out.error_items = counts.get(ItemState.ERROR, 0)
    out.done_items = counts.get(ItemState.DONE, 0)
    out.skipped_items = counts.get(ItemState.SKIPPED, 0)
    out.dropped_items = counts.get(ItemState.DROPPED, 0)
    out.progress_pct = pct
    out.scan_progress = batch.scan_progress
    out.state_history = history
    return out


def build_batch_card(batch: Batch, session: Session) -> BatchCard:
    counts = _batch_item_counts(batch.id, session)
    total = sum(counts.values())
    return BatchCard(
        id=batch.id,
        name=batch.name,
        state=batch.state,
        total_items=total,
        awaiting_review_items=counts.get(ItemState.AWAITING_REVIEW, 0),
        approved_items=counts.get(ItemState.APPROVED, 0),
        error_items=counts.get(ItemState.ERROR, 0),
        progress_pct=_progress_pct(counts),
        scan_progress=batch.scan_progress,
        schedule_at=batch.schedule_at,
        last_state_change_at=batch.last_state_change_at,
        last_error_reason=batch.last_error_reason,
        status_category=_batch_status_category(batch),
    )


def build_project_out(project: Project, session: Session) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    batches = project.batches
    out.total_batches = len(batches)
    out.active_batches = sum(1 for b in batches if b.state in _ACTIVE_STATES)
    out.error_batches = sum(1 for b in batches if b.state == BatchState.ERROR)
    out.awaiting_review_batches = sum(
        1 for b in batches if b.state == BatchState.AWAITING_REVIEW
    )
    # Awaiting review items across all batches.
    awaiting = (
        session.query(func.count(ImageItem.id))
        .join(Batch)
        .filter(
            Batch.project_id == project.id,
            ImageItem.state == ItemState.AWAITING_REVIEW,
        )
        .scalar()
        or 0
    )
    out.awaiting_review_items = int(awaiting)
    # Last activity = latest last_state_change_at across batches.
    latest: datetime | None = None
    for b in batches:
        if b.last_state_change_at:
            if latest is None or b.last_state_change_at > latest:
                latest = b.last_state_change_at
    out.last_activity_at = latest
    return out


def _project_status_category(project: Project) -> str:
    batches = project.batches
    if any(b.state == BatchState.ERROR for b in batches):
        return "error"
    if any(b.state == BatchState.AWAITING_REVIEW for b in batches):
        return "review"
    if any(b.state in _ACTIVE_STATES for b in batches):
        return "active"
    return "idle"


def build_project_card(project: Project, session: Session) -> ProjectCard:
    po = build_project_out(project, session)
    return ProjectCard(
        id=project.id,
        name=project.name,
        description=project.description,
        total_batches=po.total_batches,
        active_batches=po.active_batches,
        error_batches=po.error_batches,
        awaiting_review_batches=po.awaiting_review_batches,
        awaiting_review_items=po.awaiting_review_items,
        last_activity_at=po.last_activity_at,
        status_category=_project_status_category(project),
    )


def server_summary_counts(session: Session, queue_depth: int) -> dict[str, int]:
    """Return raw counts for the server summary bar."""
    total_projects = session.query(func.count(Project.id)).scalar() or 0
    active_batches = (
        session.query(func.count(Batch.id))
        .filter(Batch.state.in_([s.value for s in _ACTIVE_STATES]))
        .scalar()
        or 0
    )
    awaiting_review_items = (
        session.query(func.count(ImageItem.id))
        .filter(ImageItem.state == ItemState.AWAITING_REVIEW)
        .scalar()
        or 0
    )
    scheduled_batches = (
        session.query(func.count(Batch.id))
        .filter(Batch.state == BatchState.SCHEDULED)
        .scalar()
        or 0
    )
    error_batches = (
        session.query(func.count(Batch.id))
        .filter(Batch.state == BatchState.ERROR)
        .scalar()
        or 0
    )
    return {
        "total_projects": int(total_projects),
        "active_batches": int(active_batches),
        "awaiting_review_items": int(awaiting_review_items),
        "scheduled_batches": int(scheduled_batches),
        "error_batches": int(error_batches),
        "queue_depth": queue_depth,
    }
