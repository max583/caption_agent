"""Server-wide summary endpoint (D-090 — Projects list summary bar)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..schemas.summary import ServerSummary
from ..storage.session import get_session
from .deps import get_queue
from .stats import server_summary_counts

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=ServerSummary)
def get_summary(session: Session = Depends(get_session)) -> ServerSummary:
    try:
        q = get_queue()
        depth = q.qsize()
    except Exception:  # noqa: BLE001
        depth = 0
    counts = server_summary_counts(session, depth)
    return ServerSummary(**counts)
