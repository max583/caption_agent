"""Admin API endpoints — server management actions."""

from __future__ import annotations

import os
import sys
import threading

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..logging_setup.system_logger import get_system_logger

router = APIRouter()


@router.post("/api/admin/restart")
async def restart_server() -> JSONResponse:
    """Re-execute the current process to apply code or config changes.

    Returns 200 immediately, then restarts after a short delay so the
    response reaches the browser before the process exits.
    """
    log = get_system_logger()
    log.info("Admin: server restart requested via API")

    def _do_restart() -> None:
        log.info("Admin: restarting now — os.execv")
        # When launched via `python -m caption_agent.main`, sys.argv[0] is the
        # path to main.py without the -m flag, so naive execv breaks relative
        # imports.  Detect -m invocation via __main__.__spec__ and reconstruct
        # the correct command.
        import __main__  # noqa: PLC0415
        spec = getattr(getattr(__main__, "__spec__", None), "name", None)
        if spec:
            # e.g. "caption_agent.main" → python -m caption_agent.main [args…]
            restart_args = [sys.executable, "-m", spec] + sys.argv[1:]
        else:
            # Launched via installed entry-point script — argv is already correct
            restart_args = [sys.executable] + sys.argv
        log.info("Admin: exec %s", restart_args)
        os.execv(sys.executable, restart_args)

    threading.Timer(0.5, _do_restart).start()
    return JSONResponse({"ok": True, "message": "Сервер перезапускается..."})
