"""FastAPI app entry point for caption-agent v1 server.

Phase 3: adds REST API endpoints and HTMX/Jinja2 HTML UI on top of Phase 2 orchestration.

Run with:
    caption-agent-server
or:
    python -m caption_agent.main
or:
    uvicorn caption_agent.main:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import traceback

from urllib.parse import urlencode, parse_qsl

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .api import deps
from .api import pages as pages_module
from .api.admin import router as admin_router
from .api.help import router as help_router, set_templates as help_set_templates
from .api.batches import router as batches_router
from .api.config import router as config_router
from .api.filesystem import router as filesystem_router
from .api.items import router as items_router
from .api.llm_profiles import router as llm_profiles_router
from .api.logs import router as logs_router
from .api.pages import router as pages_router
from .api.projects import router as projects_router
from .api.summary import router as summary_router
from .config import ConfigManager, get_bootstrap_settings
from .logging_setup import get_system_logger, init_system_logging, set_log_level
from .orchestration.batch_processor import run_batch
from .orchestration.queue import BatchQueue, recover_and_load
from .orchestration.scheduler import scheduler_loop
from .storage import init_engine, session_scope

# Module-level queue and background task handles (populated in lifespan).
_queue: BatchQueue | None = None
_scheduler_stop: asyncio.Event | None = None
_scheduler_task: asyncio.Task | None = None
_processor_task: asyncio.Task | None = None

# Paths relative to this package.
_PKG_DIR = Path(__file__).parent
_REPO_ROOT = _PKG_DIR.parent  # scripts/caption_agent/
_TEMPLATES_DIR = _REPO_ROOT / "templates"
_STATIC_DIR = _REPO_ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _queue, _scheduler_stop, _scheduler_task, _processor_task

    settings = get_bootstrap_settings()
    settings.ensure_directories()

    init_system_logging(
        log_file=settings.log_file,
        level=settings.log_level,
        max_bytes=settings.log_rotate_max_bytes,
        backup_count=settings.log_rotate_backup_count,
    )
    logger = get_system_logger()
    logger.info("Caption agent server starting on %s:%d", settings.host, settings.port)
    logger.info("DB URL: %s", settings.db_url)

    init_engine(settings.db_url, echo=settings.db_echo)

    # Seed runtime config defaults if DB is fresh.
    with session_scope() as session:
        manager = ConfigManager(session)
        manager.seed_defaults_if_missing()
        # Apply the DB-stored log level (overrides the bootstrap default) so the
        # level chosen in Settings survives a restart.
        logging_cfg = manager.get("logging") or {}
        db_level = logging_cfg.get("log_level")
        if db_level:
            set_log_level(db_level)

    # Crash recovery + initial queue load.
    queue = BatchQueue()
    loaded = recover_and_load(queue)
    logger.info("Queue loaded with %d batch(es) from DB", loaded)
    _queue = queue

    # Wire queue into deps module so API routers can access it.
    deps.set_queue(queue)

    # Background scheduler task.
    stop_event = asyncio.Event()
    _scheduler_stop = stop_event
    _scheduler_task = asyncio.create_task(
        scheduler_loop(queue, stop_event=stop_event),
        name="caption_agent_scheduler",
    )

    # Background processing loop task.
    _processor_task = asyncio.create_task(
        _processing_loop(queue),
        name="caption_agent_processor",
    )

    logger.info("Startup complete")
    yield

    # Shutdown.
    logger.info("Caption agent server shutting down")
    stop_event.set()
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    if _processor_task:
        _processor_task.cancel()
        try:
            await _processor_task
        except asyncio.CancelledError:
            pass
    logger.info("Background tasks stopped")


async def _processing_loop(queue: BatchQueue) -> None:
    """Consume batch IDs from the queue and process them one at a time."""
    log = get_system_logger()
    while True:
        try:
            batch_id = await queue.get()
            log.info("Processing loop: dequeued batch %d", batch_id)
            await asyncio.to_thread(run_batch, batch_id)
        except asyncio.CancelledError:
            break
        except Exception:  # noqa: BLE001
            log.exception("Processing loop: unhandled error")
        finally:
            try:
                queue.task_done()
            except ValueError:
                pass


app = FastAPI(
    title="Caption Agent",
    description="LoRA training caption pipeline for LoRA training datasets (D-087/D-090)",
    version="0.4.0",
    lifespan=lifespan,
)


class _LangSwitchMiddleware(BaseHTTPMiddleware):
    """Intercept ?lang=XX, save to DB, redirect without the param (D-107)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        lang = request.query_params.get("lang")
        if lang in ("ru", "en"):
            from .config.manager import ConfigManager
            from .storage.session import session_scope

            with session_scope() as session:
                mgr = ConfigManager(session)
                ui: dict = mgr.get("ui") or {}
                ui["language"] = lang
                mgr.set("ui", ui)
                session.commit()

            # Rebuild URL without the ?lang= param, preserve other params.
            remaining = [(k, v) for k, v in parse_qsl(request.url.query) if k != "lang"]
            qs = urlencode(remaining)
            redirect_path = request.url.path + ("?" + qs if qs else "")
            return RedirectResponse(redirect_path, status_code=302)

        return await call_next(request)


app.add_middleware(_LangSwitchMiddleware)

# ---- Unhandled-exception logger ----
# Catches any 500 that would otherwise only appear on uvicorn's stderr,
# writes it to logs/server.log, then returns a plain JSON 500 response.

@app.exception_handler(Exception)
async def _log_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger = get_system_logger()
    logger.error(
        "Unhandled exception: %s %s\n%s",
        request.method,
        request.url,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error — see logs/server.log for details"},
    )


# ---- Static files ----
# Create static dir if it doesn't exist (first run).
_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ---- Jinja2 templates ----
_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Inject templates into the pages router module.
pages_module.set_templates(templates)
help_set_templates(templates)

# ---- Register API routers ----
app.include_router(admin_router)
app.include_router(projects_router)
app.include_router(batches_router)
app.include_router(items_router)
app.include_router(config_router)
app.include_router(llm_profiles_router)
app.include_router(filesystem_router)
app.include_router(logs_router)
app.include_router(summary_router)

# ---- Help documentation routes ----
app.include_router(help_router)

# ---- Register HTML page routes (last — low specificity) ----
app.include_router(pages_router)


# ---- Diagnostic endpoints (kept from Phase 2) ----

@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/queue/status")
def queue_status() -> dict[str, int]:
    """Return current in-memory queue depth."""
    return {"queued": _queue.qsize() if _queue else 0}


def run() -> None:
    """Console script entry point. Starts uvicorn server.

    Set ``CAPTION_AGENT_RELOAD=1`` for dev hot-reload (uvicorn watches the
    caption_agent package and restarts on Python changes; Jinja2 templates
    reload on every request regardless).
    """
    import uvicorn

    settings = get_bootstrap_settings()
    kwargs: dict = {
        "host": settings.host,
        "port": settings.port,
        "reload": settings.reload,
    }
    if settings.reload:
        # Watch only the package directory — avoids reloads on log/DB writes.
        kwargs["reload_dirs"] = [str(settings.app_root / "caption_agent")]
    uvicorn.run("caption_agent.main:app", **kwargs)


if __name__ == "__main__":
    run()
