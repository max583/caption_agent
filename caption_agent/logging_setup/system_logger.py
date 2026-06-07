"""Rotating file logger for system / server events.

Used by ops code (server lifecycle, configuration changes, integrity checks).
Business / domain events go to the DB via business_logger, not here.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "caption_agent.system"
_INITIALIZED = False


def init_system_logging(
    *,
    log_file: Path,
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Configure the system logger. Call once at server startup."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also echo to stderr for development.
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    _INITIALIZED = True


def get_system_logger() -> logging.Logger:
    """Return the system logger. Call init_system_logging first."""
    return logging.getLogger(_LOGGER_NAME)


def set_log_level(level: str) -> None:
    """Change the system logger level at runtime (called when Settings are saved).

    Accepts the same level strings as the stdlib: DEBUG, INFO, WARNING, ERROR.
    Unknown strings are silently ignored — the current level is preserved.

    Emits a confirmation at INFO (always visible at INFO and below) plus a DEBUG
    line, so a switch to DEBUG is immediately observable in the log even when the
    pipeline is idle.
    """
    numeric = getattr(logging, level.upper(), None)
    if numeric is None or not isinstance(numeric, int):
        return
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(numeric)
    logger.info("System log level changed to %s", level.upper())
    logger.debug("DEBUG logging is now active — verbose messages will appear here.")
