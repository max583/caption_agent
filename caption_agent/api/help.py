"""Help documentation routes (Phase 10A).

GET /help                → redirect to first page
GET /help/content/{slug} → HTML fragment (HTMX target, no base layout)
GET /help/{slug}         → two-panel help layout (full page)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config.manager import ConfigManager
from ..i18n import get_t
from ..services.help_renderer import (
    NAV_TREE,
    get_active_section_id,
    get_first_slug,
    get_page_title,
    render_page,
)
from ..storage.session import get_session

router = APIRouter(include_in_schema=False)

# Jinja2Templates instance — injected by main.py after mount (same pattern as pages.py).
_templates = None  # type: ignore[assignment]


def set_templates(templates) -> None:  # type: ignore[no-untyped-def]
    global _templates
    _templates = templates


def _get_lang(session: Session) -> str:
    try:
        ui_raw = ConfigManager(session).get("ui") or {}
        return str(ui_raw.get("language", "ru"))
    except Exception:  # noqa: BLE001
        return "ru"


# ---- Redirect /help → first page ----

@router.get("/help", response_class=RedirectResponse)
def help_root() -> RedirectResponse:
    return RedirectResponse(url=f"/help/{get_first_slug()}", status_code=302)


# ---- HTMX content fragment (registered BEFORE /help/{slug} for clarity) ----

@router.get("/help/content/{slug}", response_class=HTMLResponse)
def help_content(
    slug: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    lang = _get_lang(session)
    html = render_page(slug, lang)
    return HTMLResponse(content=html)


# ---- Full two-panel page ----

@router.get("/help/{slug}", response_class=HTMLResponse)
def help_page(
    slug: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    lang = _get_lang(session)
    t = get_t(lang)
    active_section_id = get_active_section_id(slug)
    active_title = get_page_title(slug, lang)
    return _templates.TemplateResponse(
        request,
        "help/index.html",
        {
            "nav_tree": NAV_TREE,
            "active_slug": slug,
            "active_section_id": active_section_id,
            "active_title": active_title,
            "ui_lang": lang,
            "t": t,
        },
    )
