"""Tests for Phase 10A: in-app help infrastructure."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from caption_agent.services.help_renderer import NAV_TREE, render_page, get_first_slug


# ---------------------------------------------------------------------------
# Fixtures — reuse the app client pattern from test_api.py
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient with StaticPool in-memory DB. No lifespan — matches test_api.py pattern.

    Key differences from a naive fixture:
    - StaticPool: all threads (including FastAPI's thread pool) share the same in-memory DB.
    - No `with TestClient(...)`: using `with` runs the lifespan, which calls
      init_engine(real_db_url) and overwrites the in-memory engine.
    - Queue injected via deps.set_queue so routes that call get_queue() don't 503.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from caption_agent.api import deps as _deps
    from caption_agent.main import app
    from caption_agent.models import Base
    from caption_agent.orchestration.queue import BatchQueue
    from caption_agent.storage.session import get_session

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSession()

    def override_get_session():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    _deps.set_queue(BatchQueue())

    c = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
    yield c

    session.close()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# HTTP tests (require the TestClient)
# ---------------------------------------------------------------------------

def test_help_root_redirects(client):
    """GET /help → 302 redirect to first slug."""
    resp = client.get("/help")
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith(f"/help/{get_first_slug()}")


def test_help_page_renders(client):
    """GET /help/{slug} → 200, contains sidebar and content target."""
    resp = client.get(f"/help/{get_first_slug()}", follow_redirects=True)
    assert resp.status_code == 200
    assert "help-content" in resp.text
    assert "/help/" in resp.text  # nav links present


def test_help_content_fragment_ru(client):
    """GET /help/content/{slug} → 200, is a fragment (no <html>), has <article."""
    resp = client.get(f"/help/content/{get_first_slug()}")
    assert resp.status_code == 200
    assert "<html" not in resp.text.lower()
    assert "<article" in resp.text


def test_help_content_is_not_full_page(client):
    """Content endpoint must not return a full HTML page."""
    resp = client.get(f"/help/content/{get_first_slug()}")
    assert "<!DOCTYPE" not in resp.text
    assert "<head>" not in resp.text


def test_help_content_placeholder_on_missing(client):
    """Missing slug → 200 with placeholder text (not 500)."""
    resp = client.get("/help/content/this_slug_definitely_does_not_exist_xyz")
    assert resp.status_code == 200
    # Either Russian or English placeholder text
    assert ("разработке" in resp.text or "development" in resp.text.lower())


def test_help_button_in_nav(client):
    """The ? button must appear on the main projects page."""
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert 'href="/help"' in resp.text


def test_help_all_nav_slugs_render(client):
    """First page from each section must return 200."""
    sample_slugs = [section["pages"][0]["slug"] for section in NAV_TREE]
    for slug in sample_slugs:
        resp = client.get(f"/help/content/{slug}")
        assert resp.status_code == 200, f"Failed for slug: {slug}"


# ---------------------------------------------------------------------------
# Unit tests for help_renderer (no HTTP)
# ---------------------------------------------------------------------------

def test_render_page_returns_article():
    """render_page always wraps output in <article class="help-prose">."""
    html = render_page("what_is", "ru")
    assert html.startswith('<article class="help-prose">')
    assert html.endswith("</article>")


def test_render_page_missing_slug_no_crash():
    """render_page with an unknown slug returns placeholder, not an exception."""
    html = render_page("this_does_not_exist_abc123", "ru")
    assert "<article" in html
    assert len(html) > 10


def test_render_page_md_links_rewritten():
    """Cross-page .md links must be rewritten to /help/{slug}."""
    from caption_agent.services.help_renderer import _rewrite_md_links
    raw = '<a href="concepts_trigger.md">Trigger token</a>'
    result = _rewrite_md_links(raw)
    assert 'href="/help/concepts_trigger"' in result
    assert ".md" not in result
