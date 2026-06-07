"""ImageItem endpoints: list, decide, mass-decide, image serving (D-087 / D-090)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..lifecycle.batch_states import is_valid_batch_transition
from ..logging_setup.business_logger import BusinessLogger
from ..models import Batch, ImageItem
from ..models.enums import BatchState, ItemState, ReviewDecision
from ..schemas.items import DecideRequest, ItemOut, ItemSummary, MassDecideRequest, SaveCaptionRequest
from ..storage.session import get_session
from .deps import get_batch_or_404, get_item_or_404, get_queue

router = APIRouter(tags=["items"])


def _requeue_batch_if_idle(batch_id: int, session) -> None:
    """If the batch is not already running/queued, move it to QUEUED so regenerated items get picked up."""
    batch = session.get(Batch, batch_id)
    if batch is None:
        return
    if batch.state in {BatchState.QUEUED, BatchState.PROCESSING}:
        return  # already running — processor will pick up QUEUED items
    if is_valid_batch_transition(batch.state, BatchState.QUEUED):
        batch.state = BatchState.QUEUED
        try:
            get_queue().put_nowait(batch.id)
        except Exception:  # noqa: BLE001
            pass  # queue unavailable (test context) — state change still committed

_DECIDABLE_STATES = {
    ItemState.AWAITING_REVIEW,
    ItemState.APPROVED,
    ItemState.DROPPED,
    ItemState.SKIPPED,
    ItemState.ERROR,  # error items can be regenerated, dropped, or skipped
}

_DECISION_TO_STATE = {
    ReviewDecision.ACCEPT: ItemState.APPROVED,
    ReviewDecision.DROP: ItemState.DROPPED,
    ReviewDecision.SKIP: ItemState.SKIPPED,
    ReviewDecision.REGENERATE: ItemState.QUEUED,  # re-queue for reprocessing
}


@router.get("/api/batches/{batch_id}/items", response_model=list[ItemSummary])
def list_items(
    batch_id: int,
    state: ItemState | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ItemSummary]:
    get_batch_or_404(batch_id, session)
    q = session.query(ImageItem).filter(ImageItem.batch_id == batch_id)
    if state is not None:
        q = q.filter(ImageItem.state == state)
    items = q.order_by(ImageItem.id).all()
    return [
        ItemSummary(
            id=item.id,
            file_name=item.file_name,
            state=item.state,
            decision=item.decision,
            normalized_caption=item.normalized_caption,
            warning_count=len(item.warnings) if item.warnings else 0,
            last_error_category=item.last_error_category,
        )
        for item in items
    ]


@router.get("/api/items/{item_id}", response_model=ItemOut)
def get_item(
    item_id: int,
    session: Session = Depends(get_session),
) -> ItemOut:
    item = get_item_or_404(item_id, session)
    return ItemOut.model_validate(item)


@router.post("/api/items/{item_id}/decide", response_model=ItemOut)
def decide_item(
    item_id: int,
    body: DecideRequest,
    session: Session = Depends(get_session),
) -> ItemOut:
    """Record user decision (Accept / Regenerate / Drop / Skip)."""
    item = get_item_or_404(item_id, session)
    if item.state not in _DECIDABLE_STATES:
        raise HTTPException(
            400,
            f"Item is in state {item.state!r}, which does not accept a decision",
        )
    new_state = _DECISION_TO_STATE[body.decision]
    item.state = new_state
    item.decision = body.decision
    if body.notes is not None:
        item.decision_notes = body.notes

    # On accept: lock the final caption (user-edited version or the normalized caption).
    if body.decision == ReviewDecision.ACCEPT:
        item.final_caption = body.caption if body.caption is not None else item.normalized_caption

    # If regenerating, also clear previous pipeline outputs so the processor re-runs cleanly.
    if body.decision == ReviewDecision.REGENERATE:
        item.normalized_caption = None
        item.final_caption = None
        item.raw_analyst_output = None
        item.warnings = None
        item.llm_pass_result = None
        item.normalizer_attempt = 0
        _requeue_batch_if_idle(item.batch_id, session)

    BusinessLogger(session).info(
        "item_decided",
        f"Item {item_id} ({item.file_name}): {body.decision.value}",
        batch_id=item.batch_id,
        image_item_id=item_id,
    )
    return ItemOut.model_validate(item)


@router.patch("/api/items/{item_id}/caption", response_model=ItemOut)
def save_caption(
    item_id: int,
    body: SaveCaptionRequest,
    session: Session = Depends(get_session),
) -> ItemOut:
    """Save a user-edited caption without changing the item's decision or state."""
    item = get_item_or_404(item_id, session)
    item.normalized_caption = body.caption
    BusinessLogger(session).info(
        "caption_saved",
        f"Item {item_id} ({item.file_name}): caption saved manually",
        batch_id=item.batch_id,
        image_item_id=item_id,
    )
    return ItemOut.model_validate(item)


@router.post("/api/batches/{batch_id}/items/mass-decide", response_model=dict)
def mass_decide(
    batch_id: int,
    body: MassDecideRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Apply a decision to multiple items at once."""
    get_batch_or_404(batch_id, session)

    if body.item_ids is not None:
        # Explicit IDs.
        items = (
            session.query(ImageItem)
            .filter(
                ImageItem.batch_id == batch_id,
                ImageItem.id.in_(body.item_ids),
                ImageItem.state.in_([s.value for s in _DECIDABLE_STATES]),
            )
            .all()
        )
    else:
        # All in batch matching state_filter (or AWAITING_REVIEW default).
        filter_state = body.state_filter or ItemState.AWAITING_REVIEW
        items = (
            session.query(ImageItem)
            .filter(
                ImageItem.batch_id == batch_id,
                ImageItem.state == filter_state,
            )
            .all()
        )

    # For ACCEPT: skip items with warnings unless explicitly included.
    if body.decision == ReviewDecision.ACCEPT and not body.include_with_warnings:
        items = [i for i in items if not i.warnings]

    new_state = _DECISION_TO_STATE[body.decision]
    applied = 0
    for item in items:
        item.state = new_state
        item.decision = body.decision
        if body.decision == ReviewDecision.ACCEPT:
            item.final_caption = item.normalized_caption
        if body.decision == ReviewDecision.REGENERATE:
            item.normalized_caption = None
            item.final_caption = None
            item.raw_analyst_output = None
            item.warnings = None
            item.llm_pass_result = None
            item.normalizer_attempt = 0
        applied += 1

    if applied and body.decision == ReviewDecision.REGENERATE:
        _requeue_batch_if_idle(batch_id, session)

    if applied:
        BusinessLogger(session).info(
            "mass_decide",
            f"Mass {body.decision.value}: {applied} item(s) in batch {batch_id}",
            batch_id=batch_id,
        )
    return {"applied": applied}


@router.get("/api/items/{item_id}/image")
def serve_image(
    item_id: int,
    session: Session = Depends(get_session),
) -> FileResponse:
    """Return the original image file for display in the Review tab.

    Sets ``Cache-Control: no-cache`` so the browser always revalidates via the
    ETag that FileResponse derives from file mtime. SQLite reuses item IDs
    after a batch is deleted (no AUTOINCREMENT) — without revalidation the
    browser would serve stale icons from the previous batch for the same URL.
    """
    item = get_item_or_404(item_id, session)
    path = Path(item.file_path)
    if not path.exists():
        raise HTTPException(404, f"Image file not found on disk: {item.file_path}")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(
        path=str(path),
        media_type=media_type,
        headers={"Cache-Control": "no-cache"},
    )
