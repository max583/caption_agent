"""Background scheduler: moves scheduled batches to QUEUED when their time arrives.

Per D-087:
- One-shot ``schedule_at`` per batch (no recurring schedules).
- Missed schedules (server was down) are queued immediately on startup.
- A newly scheduled batch joins the queue tail; it does not preempt running batches.

The scheduler is an asyncio coroutine that polls the DB every ``POLL_INTERVAL``
seconds.  It is started from ``main.py`` lifespan as a background task.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..models import Batch, BatchStateHistory
from ..models.enums import BatchState
from ..logging_setup.system_logger import get_system_logger
from ..storage.session import session_scope
from .queue import BatchQueue

POLL_INTERVAL: float = 15.0  # seconds


async def scheduler_loop(queue: BatchQueue, *, stop_event: asyncio.Event) -> None:
    """Poll for scheduled batches; run until *stop_event* is set."""
    log = get_system_logger()
    log.info("Scheduler started (poll interval %.0fs)", POLL_INTERVAL)
    while not stop_event.is_set():
        try:
            _tick(queue)
        except Exception:  # noqa: BLE001
            log.exception("Scheduler tick error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL)
        except asyncio.TimeoutError:
            pass
    log.info("Scheduler stopped")


def _tick(queue: BatchQueue) -> None:
    """One poll cycle: find due batches, move to QUEUED, enqueue."""
    now = datetime.now(timezone.utc)
    log = get_system_logger()

    with session_scope() as session:
        due = (
            session.query(Batch)
            .filter(
                Batch.state == BatchState.SCHEDULED,
                Batch.schedule_at <= now,
            )
            .all()
        )
        for batch in due:
            old_state = batch.state
            batch.state = BatchState.QUEUED
            batch.schedule_at = None
            batch.last_state_change_at = now
            session.add(BatchStateHistory(
                batch_id=batch.id,
                from_state=old_state.value,
                to_state=BatchState.QUEUED.value,
                reason="schedule_due",
            ))
            queue.put_nowait(batch.id)
            log.info("Batch %d moved from SCHEDULED to QUEUED (schedule due)", batch.id)
