"""Journal / business log endpoints: GET /api/logs, DELETE /api/logs (D-090)."""

from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..models import BusinessLog
from ..models.enums import LogLevel
from ..schemas.logs import LogOut, LogsPage
from ..storage.session import get_session

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=LogsPage)
def get_logs(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    level: LogLevel | None = Query(default=None),
    project_id: int | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> LogsPage:
    q = session.query(BusinessLog)
    if date_from:
        q = q.filter(BusinessLog.timestamp >= date_from)
    if date_to:
        q = q.filter(BusinessLog.timestamp <= date_to)
    if level:
        q = q.filter(BusinessLog.level == level)
    if project_id is not None:
        q = q.filter(BusinessLog.project_id == project_id)
    if batch_id is not None:
        q = q.filter(BusinessLog.batch_id == batch_id)
    if event_type:
        q = q.filter(BusinessLog.event_type == event_type)
    if search:
        q = q.filter(BusinessLog.message.ilike(f"%{search}%"))

    total = q.count()
    offset = (page - 1) * page_size
    rows = q.order_by(BusinessLog.timestamp.desc()).offset(offset).limit(page_size).all()
    pages = max(1, math.ceil(total / page_size))
    return LogsPage(
        items=[LogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.delete("", status_code=200)
def delete_logs(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    level: LogLevel | None = Query(default=None),
    project_id: int | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    q = session.query(BusinessLog)
    if date_from:
        q = q.filter(BusinessLog.timestamp >= date_from)
    if date_to:
        q = q.filter(BusinessLog.timestamp <= date_to)
    if level:
        q = q.filter(BusinessLog.level == level)
    if project_id is not None:
        q = q.filter(BusinessLog.project_id == project_id)
    if batch_id is not None:
        q = q.filter(BusinessLog.batch_id == batch_id)
    if event_type:
        q = q.filter(BusinessLog.event_type == event_type)
    if search:
        q = q.filter(BusinessLog.message.ilike(f"%{search}%"))
    deleted = q.delete(synchronize_session=False)
    return {"deleted": deleted}
