"""In-memory FIFO queue for batch IDs awaiting processing (D-087).

On server startup the queue is populated from the DB (all QUEUED batches) and
orphaned PROCESSING batches are reset to QUEUED first.  The processing loop
consumes items one at a time; the scheduler loop appends newly scheduled batches.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..models import Batch, BatchStateHistory
from ..models.enums import BatchState
from ..storage.session import session_scope


class BatchQueue:
    """Async-safe FIFO queue over asyncio.Queue.

    Thread-safe for put operations from the scheduler coroutine; the processing
    loop gets items with ``await get()``.
    """

    def __init__(self) -> None:
        self._q: asyncio.Queue[int] = asyncio.Queue()

    async def put(self, batch_id: int) -> None:
        await self._q.put(batch_id)

    def put_nowait(self, batch_id: int) -> None:
        self._q.put_nowait(batch_id)

    async def get(self) -> int:
        return await self._q.get()

    def task_done(self) -> None:
        self._q.task_done()

    def qsize(self) -> int:
        return self._q.qsize()


def recover_and_load(queue: BatchQueue) -> int:
    """Crash recovery + initial queue load.  Call once at server startup.

    1. Orphaned batches in PROCESSING → QUEUED (they lost state mid-run).
    2. All QUEUED batches → added to in-memory queue, FIFO by creation time.

    Returns the number of batch IDs loaded.
    """
    loaded = 0
    with session_scope() as session:
        now = datetime.now(timezone.utc)

        # Step 1: recover orphaned PROCESSING and SCANNING batches → QUEUED.
        # SCANNING is also recoverable: the scan phase is idempotent (uses sidecars).
        orphans = (
            session.query(Batch)
            .filter(Batch.state.in_([BatchState.PROCESSING, BatchState.SCANNING]))
            .all()
        )
        for batch in orphans:
            old_state = batch.state
            batch.state = BatchState.QUEUED
            batch.scan_progress = 0  # reset so scan restarts cleanly
            batch.last_state_change_at = now
            session.add(BatchStateHistory(
                batch_id=batch.id,
                from_state=old_state.value,
                to_state=BatchState.QUEUED.value,
                reason="crash_recovery",
            ))

        # Step 2: load all QUEUED batches into memory queue (oldest first).
        queued = (
            session.query(Batch)
            .filter(Batch.state == BatchState.QUEUED)
            .order_by(Batch.created_at)
            .all()
        )
        for batch in queued:
            queue.put_nowait(batch.id)
            loaded += 1

    return loaded
