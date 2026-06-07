"""Batch CRUD and lifecycle endpoints (D-087 / D-090)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..lifecycle.batch_states import is_valid_batch_transition
from ..logging_setup.business_logger import BusinessLogger
from ..logging_setup.system_logger import get_system_logger
from ..models import Batch, BatchStateHistory, ImageItem, Project
from ..models.enums import BatchState, ItemState, SourceType, BranchType
from ..pipeline.exporter import export_batch
from ..schemas.batches import BatchCard, BatchCreate, BatchOut, BatchUpdate
from ..storage.session import get_session
from .deps import get_batch_or_404, get_project_or_404, get_queue
from .stats import build_batch_card, build_batch_out

router = APIRouter(tags=["batches"])

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# Item states that must be resolved before a batch can be exported/finalized.
# A decided item is APPROVED / DROPPED / SKIPPED (or terminal ERROR/DONE); anything
# still awaiting review or actively processing blocks the export.
_PENDING_EXPORT_STATES = (
    ItemState.QUEUED,
    ItemState.READING_CONTEXT,
    ItemState.ANALYZING,
    ItemState.NORMALIZING,
    ItemState.RULE_CHECK,
    ItemState.LLM_PASS_CHECK,
    ItemState.REGENERATING,
    ItemState.AWAITING_REVIEW,
)

# Batch states where editing is blocked.
_BUSY_BATCH_STATES = {BatchState.PROCESSING, BatchState.SCANNING}


# ---- Project-scoped batch list + create ----

@router.get("/api/projects/{project_id}/batches", response_model=list[BatchCard])
def list_batches(
    project_id: int,
    session: Session = Depends(get_session),
) -> list[BatchCard]:
    get_project_or_404(project_id, session)
    batches = (
        session.query(Batch)
        .filter(Batch.project_id == project_id)
        .order_by(Batch.created_at.desc())
        .all()
    )
    return [build_batch_card(b, session) for b in batches]


@router.post(
    "/api/projects/{project_id}/batches",
    response_model=BatchOut,
    status_code=status.HTTP_201_CREATED,
)
def create_batch(
    project_id: int,
    body: BatchCreate,
    session: Session = Depends(get_session),
) -> BatchOut:
    project = get_project_or_404(project_id, session)
    batch = Batch(
        project_id=project_id,
        name=body.name,
        source_folder_path=body.source_folder_path,
        source_type=body.source_type or project.default_source_type,
        branch=body.branch or project.default_branch,
        state=BatchState.SCHEDULED if body.schedule_at else BatchState.QUEUED,
        schedule_at=body.schedule_at,
        normalizer_max_retries_override=body.normalizer_max_retries_override,
        consecutive_failure_threshold_override=body.consecutive_failure_threshold_override,
    )
    session.add(batch)
    session.flush()
    session.add(BatchStateHistory(
        batch_id=batch.id,
        from_state=None,
        to_state=batch.state.value,
        reason="created",
    ))
    BusinessLogger(session).info(
        "batch_created",
        f"Batch created: {batch.name!r} in project {project_id}",
        project_id=project_id,
        batch_id=batch.id,
    )

    log = get_system_logger()
    log.debug(
        "[create_batch] batch %d (%r) created in project %d — folder: %s, state: %s",
        batch.id, batch.name, project_id, batch.source_folder_path, batch.state.value,
    )

    # Auto-scan the source folder on creation so the batch is populated immediately.
    # A missing/invalid folder is not fatal here — the batch is still created with
    # zero items and can be scanned later via the Scan button.
    try:
        n = _scan_folder_into_batch(batch, session)
        log.debug("[create_batch] batch %d — auto-scan added %d item(s)", batch.id, n)
    except HTTPException as exc:
        log.debug("[create_batch] batch %d — auto-scan skipped: %s", batch.id, exc.detail)

    # Put immediately-runnable batches into the in-memory processing queue.
    # Without this, batches created after server startup stay QUEUED in DB forever
    # because recover_and_load only runs once at startup.
    if batch.state == BatchState.QUEUED:
        try:
            get_queue().put_nowait(batch.id)
            log.debug("[create_batch] batch %d — added to processing queue", batch.id)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[create_batch] batch %d — could not enqueue: %s (scheduler will retry)", batch.id, exc
            )

    return build_batch_out(batch, session)


# ---- Single batch CRUD ----

@router.get("/api/batches/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    batch = get_batch_or_404(batch_id, session)
    return build_batch_out(batch, session)


@router.patch("/api/batches/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: int,
    body: BatchUpdate,
    session: Session = Depends(get_session),
) -> BatchOut:
    batch = get_batch_or_404(batch_id, session)
    if batch.state in _BUSY_BATCH_STATES:
        raise HTTPException(400, f"Cannot edit a batch in {batch.state.value} state")
    if body.name is not None:
        batch.name = body.name
    if body.source_type is not None:
        batch.source_type = body.source_type
    if body.branch is not None:
        batch.branch = body.branch
    if body.schedule_at is not None:
        batch.schedule_at = body.schedule_at
    if body.normalizer_max_retries_override is not None:
        batch.normalizer_max_retries_override = body.normalizer_max_retries_override
    if body.consecutive_failure_threshold_override is not None:
        batch.consecutive_failure_threshold_override = body.consecutive_failure_threshold_override
    BusinessLogger(session).info(
        "batch_updated", f"Batch {batch_id} updated", batch_id=batch_id
    )
    return build_batch_out(batch, session)


@router.delete("/api/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> None:
    log = get_system_logger()
    batch = get_batch_or_404(batch_id, session)
    log.debug(
        "[delete_batch] request: batch %d (%r) state=%s items=%d",
        batch_id, batch.name, batch.state.value,
        session.query(ImageItem).filter(ImageItem.batch_id == batch_id).count(),
    )
    if batch.state == BatchState.PROCESSING:
        log.debug("[delete_batch] batch %d — rejected: currently processing", batch_id)
        raise HTTPException(400, "Cannot delete a batch that is currently processing. Abort it first.")
    BusinessLogger(session).info(
        "batch_deleted", f"Batch deleted: {batch.name!r} (id={batch_id})",
        batch_id=batch_id,
    )
    session.delete(batch)
    log.debug("[delete_batch] batch %d (%r) — deleted (cascade removes items + history)", batch_id, batch.name)


# ---- Scan ----

def _scan_folder_into_batch(batch: Batch, session: Session) -> int:
    """Sync ImageItem rows with the batch's source folder.

    - Adds rows for new image files found in the folder.
    - Removes rows (and their JSON sidecars) for images that no longer exist on disk.

    Idempotent. Returns the number of items added (removals logged separately).
    Raises HTTPException(400) if the folder is missing or not a directory.
    """
    folder = Path(batch.source_folder_path)
    if not folder.exists():
        raise HTTPException(400, f"Source folder does not exist: {folder}")
    if not folder.is_dir():
        raise HTTPException(400, f"Source folder path is not a directory: {folder}")

    log = get_system_logger()

    existing_items: list[ImageItem] = (
        session.query(ImageItem).filter(ImageItem.batch_id == batch.id).all()
    )
    existing_by_path = {item.file_path: item for item in existing_items}

    log.debug(
        "[scan_folder] batch %d — scanning %s (already have %d item(s))",
        batch.id, folder, len(existing_by_path),
    )

    # ── Remove items whose image files have been deleted from disk ──────────
    removed = 0
    for file_path, item in list(existing_by_path.items()):
        if not Path(file_path).exists():
            # Delete associated JSON sidecar if present.
            sidecar = Path(file_path).with_suffix(".json")
            if sidecar.exists():
                try:
                    sidecar.unlink()
                    log.debug("[scan_folder] batch %d — deleted sidecar: %s", batch.id, sidecar.name)
                except OSError as exc:
                    log.warning("[scan_folder] batch %d — could not delete sidecar %s: %s", batch.id, sidecar.name, exc)
            session.delete(item)
            del existing_by_path[file_path]
            log.debug("[scan_folder] batch %d — removed missing item: %s", batch.id, item.file_name)
            removed += 1

    # ── Add rows for new image files ─────────────────────────────────────────
    added = 0
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in _IMAGE_EXTENSIONS:
            continue
        path_str = str(p)
        if path_str in existing_by_path:
            log.debug("[scan_folder] batch %d — skip (already present): %s", batch.id, p.name)
            continue
        session.add(ImageItem(
            batch_id=batch.id,
            file_path=path_str,
            file_name=p.name,
            state=ItemState.QUEUED,
        ))
        log.debug("[scan_folder] batch %d — queued: %s", batch.id, p.name)
        added += 1

    log.debug("[scan_folder] batch %d — done: %d added, %d removed", batch.id, added, removed)
    BusinessLogger(session).info(
        "batch_scanned",
        f"Batch {batch.id} scanned: {added} new item(s) added, {removed} missing item(s) removed from {folder}",
        batch_id=batch.id,
    )
    return added


@router.post("/api/batches/{batch_id}/scan", response_model=BatchOut)
def scan_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Scan source_folder_path and create ImageItem rows for found image files.

    Idempotent: skips files already present in the batch. Only allowed when
    batch is not currently PROCESSING.
    """
    batch = get_batch_or_404(batch_id, session)
    if batch.state in _BUSY_BATCH_STATES:
        raise HTTPException(400, f"Cannot scan while batch is {batch.state.value}")

    _scan_folder_into_batch(batch, session)
    return build_batch_out(batch, session)


# ---- Lifecycle actions ----

def _transition_batch_api(
    batch: Batch,
    to_state: BatchState,
    reason: str,
    session: Session,
) -> None:
    """Validate and perform a batch state transition; raise HTTP 409 on invalid."""
    log = get_system_logger()
    log.debug(
        "[batch_transition] batch %d (%r): %s → %s (reason=%s)",
        batch.id, batch.name, batch.state.value, to_state.value, reason,
    )
    if not is_valid_batch_transition(batch.state, to_state):
        log.debug(
            "[batch_transition] batch %d — rejected: invalid transition %s → %s",
            batch.id, batch.state.value, to_state.value,
        )
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition batch from {batch.state!r} to {to_state!r}",
        )
    old = batch.state
    batch.state = to_state
    batch.last_state_change_at = datetime.now(timezone.utc)
    session.add(BatchStateHistory(
        batch_id=batch.id,
        from_state=old.value,
        to_state=to_state.value,
        reason=reason,
    ))
    BusinessLogger(session).info(
        "batch_state_change",
        f"Batch {batch.id}: {old.value} → {to_state.value} ({reason})",
        batch_id=batch.id,
    )
    log.debug("[batch_transition] batch %d — transition recorded", batch.id)


@router.post("/api/batches/{batch_id}/queue", response_model=BatchOut)
def queue_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Move batch to QUEUED state and enqueue it for processing."""
    batch = get_batch_or_404(batch_id, session)
    _transition_batch_api(batch, BatchState.QUEUED, "manually_queued", session)
    session.flush()
    q = get_queue()
    q.put_nowait(batch_id)
    return build_batch_out(batch, session)


@router.post("/api/batches/{batch_id}/pause", response_model=BatchOut)
def pause_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Request a pause.  The processor will stop before the next item."""
    batch = get_batch_or_404(batch_id, session)
    _transition_batch_api(batch, BatchState.PAUSED, "user_pause", session)
    return build_batch_out(batch, session)


@router.post("/api/batches/{batch_id}/resume", response_model=BatchOut)
def resume_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Resume a PAUSED or ERROR batch by re-queuing it."""
    batch = get_batch_or_404(batch_id, session)
    _transition_batch_api(batch, BatchState.QUEUED, "user_resume", session)
    session.flush()
    q = get_queue()
    q.put_nowait(batch_id)
    return build_batch_out(batch, session)


@router.post("/api/batches/{batch_id}/abort", response_model=BatchOut)
def abort_batch(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Abort a PROCESSING or PAUSED batch by moving it to ERROR."""
    batch = get_batch_or_404(batch_id, session)
    _transition_batch_api(batch, BatchState.ERROR, "user_abort", session)
    batch.last_error_reason = "Aborted by user"
    return build_batch_out(batch, session)


@router.post("/api/batches/{batch_id}/export", response_model=BatchOut)
def export_batch_endpoint(
    batch_id: int,
    session: Session = Depends(get_session),
) -> BatchOut:
    """Export approved captions as .txt sidecars and move batch to DONE."""
    batch = get_batch_or_404(batch_id, session)
    if batch.state not in {BatchState.AWAITING_REVIEW, BatchState.DONE}:
        raise HTTPException(
            400,
            f"Export only available from AWAITING_REVIEW or DONE state, current: {batch.state!r}",
        )

    # Refuse to finalize while items are still pending review or in-flight —
    # otherwise the batch would move to DONE with un-reviewed items left behind.
    pending = (
        session.query(ImageItem)
        .filter(
            ImageItem.batch_id == batch_id,
            ImageItem.state.in_(_PENDING_EXPORT_STATES),
        )
        .count()
    )
    if pending:
        raise HTTPException(
            400,
            f"{pending} item(s) still pending review or processing. "
            "Decide (accept / drop / skip) all items before exporting.",
        )

    _transition_batch_api(batch, BatchState.EXPORTING, "export_triggered", session)
    session.flush()
    try:
        written = export_batch(batch, session)
    except Exception as exc:
        raise HTTPException(500, f"Export failed: {exc}") from exc

    _transition_batch_api(batch, BatchState.DONE, f"exported_{written}_items", session)
    BusinessLogger(session).info(
        "batch_exported",
        f"Batch {batch_id} exported: {written} caption(s) written",
        batch_id=batch_id,
    )
    return build_batch_out(batch, session)
