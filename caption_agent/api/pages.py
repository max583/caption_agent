"""HTML page routes for the HTMX/Alpine/Tailwind UI (D-090).

Each route renders a full-page Jinja2 template. HTMX polling targets
/partials/* sub-routes for incremental updates.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config.manager import ConfigManager
from ..config.schema import PollingConfig
from ..i18n import get_t
from ..models import Batch, BusinessLog, ImageItem, LLMProfile, Project
from ..models.enums import BatchState, ItemState, LogLevel
from ..storage.session import get_session
from .deps import get_batch_or_404, get_project_or_404, get_queue
from .stats import (
    build_batch_card,
    build_batch_out,
    build_project_card,
    server_summary_counts,
)

router = APIRouter(include_in_schema=False)

# Jinja2Templates instance injected by main.py after mount.
_templates = None  # type: ignore[assignment]


def set_templates(templates) -> None:  # type: ignore[no-untyped-def]
    global _templates
    _templates = templates


def _r(
    request: Request,
    template: str,
    context: dict,
    session: Session | None = None,
) -> HTMLResponse:
    """Render a Jinja2 template, injecting ui_lang and translation dict t (D-107)."""
    if session is not None:
        try:
            ui_raw = ConfigManager(session).get("ui") or {}
            ui_lang: str = ui_raw.get("language", "ru")
        except Exception:  # noqa: BLE001
            ui_lang = "ru"
    else:
        ui_lang = "ru"
    context.setdefault("ui_lang", ui_lang)
    context.setdefault("t", get_t(ui_lang))
    # Starlette 0.36+ (FastAPI 0.110+): TemplateResponse(request, name, context).
    # The new API injects "request" into context automatically.
    return _templates.TemplateResponse(request, template, context)


def _polling_cfg(session: Session) -> PollingConfig:
    try:
        raw = ConfigManager(session).get("polling") or {}
        return PollingConfig.model_validate(raw)
    except Exception:  # noqa: BLE001
        return PollingConfig()


# ---- Projects list ----

@router.get("/", response_class=HTMLResponse)
def projects_list(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    projects = session.query(Project).order_by(Project.created_at.desc()).all()
    cards = [build_project_card(p, session) for p in projects]
    # Sort: errors first, then review, then active, then idle.
    _order = {"error": 0, "review": 1, "active": 2, "idle": 3}
    cards.sort(key=lambda c: _order.get(c.status_category, 99))

    try:
        depth = get_queue().qsize()
    except Exception:  # noqa: BLE001
        depth = 0
    summary = server_summary_counts(session, depth)
    poll = _polling_cfg(session)
    return _r(request, "projects/list.html", {
        "cards": cards,
        "summary": summary,
        "poll_interval": poll.projects_list,
    }, session=session)


# ---- Partials: server summary bar (polled) ----

@router.get("/partials/summary", response_class=HTMLResponse)
def partial_summary(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    try:
        depth = get_queue().qsize()
    except Exception:  # noqa: BLE001
        depth = 0
    summary = server_summary_counts(session, depth)
    return _r(request, "partials/server_summary.html", {"summary": summary}, session=session)


# ---- Project workspace ----

@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_workspace(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    project = get_project_or_404(project_id, session)
    batches = (
        session.query(Batch)
        .filter(Batch.project_id == project_id)
        .order_by(Batch.created_at.desc())
        .all()
    )
    batch_cards = [build_batch_card(b, session) for b in batches]
    poll = _polling_cfg(session)
    return _r(request, "projects/workspace.html", {
        "project": project,
        "batch_cards": batch_cards,
        "poll_interval": poll.project_workspace,
    }, session=session)


# ---- Partial: batch cards for project workspace ----

@router.get("/partials/projects/{project_id}/batches", response_class=HTMLResponse)
def partial_batch_cards(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    project = get_project_or_404(project_id, session)
    batches = (
        session.query(Batch)
        .filter(Batch.project_id == project_id)
        .order_by(Batch.created_at.desc())
        .all()
    )
    batch_cards = [build_batch_card(b, session) for b in batches]
    return _r(request, "partials/batch_cards.html", {
        "project": project,
        "batch_cards": batch_cards,
    }, session=session)


# ---- Batch form ----

@router.get("/projects/{project_id}/batches/{batch_id}", response_class=HTMLResponse)
def batch_form(
    project_id: int,
    batch_id: int,
    tab: str = Query(default="overview"),
    item_id: int | None = Query(default=None),
    request: Request = None,  # type: ignore[assignment]
    session: Session = Depends(get_session),
) -> HTMLResponse:
    project = get_project_or_404(project_id, session)
    batch = get_batch_or_404(batch_id, session)
    if batch.project_id != project_id:
        from fastapi import HTTPException
        raise HTTPException(404, "Batch does not belong to this project")

    batch_out = build_batch_out(batch, session)

    # Items for the Items and Review tabs.
    items = (
        session.query(ImageItem)
        .filter(ImageItem.batch_id == batch_id)
        .order_by(ImageItem.id)
        .all()
    )

    # Selected item for Review tab.
    selected_item = None
    if tab == "review" and item_id:
        selected_item = session.get(ImageItem, item_id)
    elif tab == "review" and items:
        # Default: first awaiting review, or first item.
        selected_item = next(
            (i for i in items if i.state == ItemState.AWAITING_REVIEW),
            items[0] if items else None,
        )

    poll = _polling_cfg(session)
    poll_interval = (
        poll.batch_processing
        if batch.state == BatchState.PROCESSING
        else poll.batch_idle
    )

    return _r(request, "batches/form.html", {
        "project": project,
        "batch": batch,
        "batch_out": batch_out,
        "items": items,
        "selected_item": selected_item,
        "tab": tab,
        "poll_interval": poll_interval,
    }, session=session)


# ---- Partial: batch header (progress + state, polled) ----

@router.get("/partials/batches/{batch_id}/header", response_class=HTMLResponse)
def partial_batch_header(
    batch_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    batch = get_batch_or_404(batch_id, session)
    batch_out = build_batch_out(batch, session)
    return _r(request, "partials/batch_header.html", {"batch": batch, "batch_out": batch_out}, session=session)


# ---- Partial: batch items table (polled) ----

@router.get("/partials/batches/{batch_id}/items", response_class=HTMLResponse)
def partial_batch_items(
    batch_id: int,
    state: str | None = Query(default=None),
    request: Request = None,  # type: ignore[assignment]
    session: Session = Depends(get_session),
) -> HTMLResponse:
    batch = get_batch_or_404(batch_id, session)
    q = session.query(ImageItem).filter(ImageItem.batch_id == batch_id)
    if state:
        q = q.filter(ImageItem.state == state)
    items = q.order_by(ImageItem.id).all()
    return _r(request, "partials/batch_items.html", {"batch": batch, "items": items}, session=session)


# ---- Partial: review right-pane detail ----

@router.get("/partials/items/{item_id}/detail", response_class=HTMLResponse)
def partial_item_detail(
    item_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    item = session.get(ImageItem, item_id)
    if item is None:
        return HTMLResponse("<div class='text-gray-400 p-4'>Item not found</div>")
    return _r(request, "partials/item_detail.html", {"item": item}, session=session)


# ---- Partial: project analysis (D-108 / D-108a) ----

@router.get("/partials/projects/{project_id}/analysis", response_class=HTMLResponse)
def partial_project_analysis(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    from ..analysis.dataset_stats import compute_project_stats
    from ..analysis.llm_analysis import run_dataset_llm_analysis
    from ..config.manager import ConfigManager
    from ..logging_setup.system_logger import get_system_logger

    project = get_project_or_404(project_id, session)
    stats = compute_project_stats(project_id, session, lora_type=str(project.lora_type))

    llm_recs = None
    try:
        llm_cfg = ConfigManager(session).get_main_llm()
        llm_recs = run_dataset_llm_analysis(
            project_id=project_id,
            lora_type=str(project.lora_type),
            stats=stats,
            session=session,
            llm_cfg=llm_cfg,
        )
    except Exception as exc:  # noqa: BLE001
        get_system_logger().warning(
            "Dataset LLM analysis failed for project %d: %s", project_id, exc
        )

    return _r(request, "partials/project_analysis.html", {
        "project": project,
        "stats": stats,
        "llm_recs": llm_recs,
    }, session=session)


# ---- Partial: project caption policy (D-114) ----

@router.get("/partials/projects/{project_id}/policy", response_class=HTMLResponse)
def partial_project_policy(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    from ..schemas.policy import get_project_policy  # noqa: PLC0415

    project = get_project_or_404(project_id, session)
    policy = get_project_policy(project)
    is_default = project.caption_policy is None
    return _r(request, "partials/project_policy.html", {
        "project": project,
        "policy": policy,
        "is_default": is_default,
    }, session=session)


# ---- Settings ----

@router.get("/settings", response_class=RedirectResponse)
def settings_redirect() -> RedirectResponse:
    return RedirectResponse(url="/settings/llm", status_code=302)


@router.get("/settings/{section}", response_class=HTMLResponse)
def settings_page(
    section: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    mgr = ConfigManager(session)
    cfg = mgr.all()
    valid_sections = ["llm", "retry", "polling", "paths", "logging", "database", "ui"]
    if section not in valid_sections:
        section = "llm"

    profiles = []
    if section == "llm":
        profiles = session.query(LLMProfile).order_by(LLMProfile.created_at).all()

    return _r(request, "settings/index.html", {
        "section": section,
        "sections": valid_sections,
        "cfg": cfg,
        "profiles": profiles,
    }, session=session)


# ---- Journal ----

@router.get("/journal", response_class=HTMLResponse)
def journal_page(
    request: Request,
    project_id: int | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    level: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    import math

    page_size = 50
    q = session.query(BusinessLog)
    if project_id is not None:
        q = q.filter(BusinessLog.project_id == project_id)
    if batch_id is not None:
        q = q.filter(BusinessLog.batch_id == batch_id)
    if level:
        q = q.filter(BusinessLog.level == level)

    total = q.count()
    offset = (page - 1) * page_size
    logs = q.order_by(BusinessLog.timestamp.desc()).offset(offset).limit(page_size).all()
    pages = max(1, math.ceil(total / page_size))

    # Get project / batch names for filter dropdowns.
    all_projects = session.query(Project).order_by(Project.name).all()
    log_levels = [lv.value for lv in LogLevel]

    return _r(request, "journal/index.html", {
        "logs": logs,
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": page_size,
        "filter_project_id": project_id,
        "filter_batch_id": batch_id,
        "filter_level": level,
        "all_projects": all_projects,
        "log_levels": log_levels,
    }, session=session)
