"""Business-process logger backed by the BusinessLog table.

Per D-087: lifecycle transitions, user decisions, errors with reasons. Viewable in UI Journal.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import BusinessLog
from ..models.enums import LogLevel


class BusinessLogger:
    """Session-scoped logger that writes to the business_logs table.

    Caller is responsible for committing the session (FastAPI dependency `get_session` does this).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def log(
        self,
        *,
        event_type: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        project_id: int | None = None,
        batch_id: int | None = None,
        image_item_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> BusinessLog:
        """Record one business log entry. Does not commit — caller commits."""
        entry = BusinessLog(
            event_type=event_type,
            message=message,
            level=level,
            project_id=project_id,
            batch_id=batch_id,
            image_item_id=image_item_id,
            details=details,
        )
        self._session.add(entry)
        return entry

    def info(self, event_type: str, message: str, **kwargs: Any) -> BusinessLog:
        return self.log(event_type=event_type, message=message, level=LogLevel.INFO, **kwargs)

    def warning(self, event_type: str, message: str, **kwargs: Any) -> BusinessLog:
        return self.log(event_type=event_type, message=message, level=LogLevel.WARNING, **kwargs)

    def error(self, event_type: str, message: str, **kwargs: Any) -> BusinessLog:
        return self.log(event_type=event_type, message=message, level=LogLevel.ERROR, **kwargs)


def log_event(session: Session, **kwargs: Any) -> BusinessLog:
    """Convenience shortcut: instantiate a logger and log once."""
    return BusinessLogger(session).log(**kwargs)
