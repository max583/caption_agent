"""Integration tests for Phase 3 REST API endpoints.

Uses FastAPI TestClient with a dedicated in-memory SQLite database backed by
StaticPool so all threads (including FastAPI's thread pool) share the same
connection and thus the same in-memory database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from caption_agent.main import app
from caption_agent.models import Base, Batch, BatchStateHistory, ImageItem, Project
from caption_agent.models.enums import BatchState, BranchType, ItemState, ReviewDecision, SourceType
from caption_agent.storage.session import get_session


# ---------------------------------------------------------------------------
# Shared in-memory engine (StaticPool so all threads see the same DB)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def api_engine():
    """Dedicated SQLite in-memory engine with StaticPool for API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def api_session(api_engine) -> Session:
    """Session bound to the StaticPool in-memory engine."""
    SessionLocal = sessionmaker(bind=api_engine, expire_on_commit=False)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def client(api_session: Session):
    """TestClient with the API DB session overridden to the StaticPool session.

    Uses TestClient WITHOUT 'with' context so the lifespan does NOT run
    (lifespan would call init_engine(real_db_url), overwriting the global engine).
    """
    from caption_agent.api import deps as _deps
    from caption_agent.orchestration.queue import BatchQueue

    def _override():
        try:
            yield api_session
            api_session.commit()
        except Exception:
            api_session.rollback()
            raise

    app.dependency_overrides[get_session] = _override
    # Provide a real queue so lifecycle endpoints that call get_queue() don't 503.
    _deps.set_queue(BatchQueue())

    c = TestClient(app, raise_server_exceptions=True)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project(api_session: Session) -> Project:
    p = Project(name="Test Project", description="desc")
    api_session.add(p)
    api_session.flush()
    return p


@pytest.fixture
def batch(api_session: Session, project: Project) -> Batch:
    b = Batch(
        project_id=project.id,
        name="test_batch",
        source_folder_path="/tmp/src",
        state=BatchState.QUEUED,
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    api_session.add(b)
    api_session.flush()
    api_session.add(BatchStateHistory(batch_id=b.id, to_state=BatchState.QUEUED, reason="created"))
    return b


@pytest.fixture
def item(api_session: Session, batch: Batch) -> ImageItem:
    i = ImageItem(
        batch_id=batch.id,
        file_path="/tmp/src/img.png",
        file_name="img.png",
        state=ItemState.AWAITING_REVIEW,
        normalized_caption="mychar01, portrait",
    )
    api_session.add(i)
    api_session.flush()
    return i


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def test_summary_returns_counts(client):
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_projects" in data
    assert "active_batches" in data


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def test_create_project(client):
    resp = client.post("/api/projects", json={"name": "P1"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "P1"
    assert data["id"] > 0


def test_create_project_duplicate_name(client, project):
    resp = client.post("/api/projects", json={"name": "Test Project"})
    assert resp.status_code == 409


def test_list_projects(client, project):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(p["name"] == "Test Project" for p in data)


def test_get_project(client, project):
    resp = client.get(f"/api/projects/{project.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Project"


def test_get_project_not_found(client):
    resp = client.get("/api/projects/9999")
    assert resp.status_code == 404


def test_update_project(client, project):
    resp = client.patch(f"/api/projects/{project.id}", json={"description": "updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"


def test_delete_project(client, project):
    resp = client.delete(f"/api/projects/{project.id}")
    assert resp.status_code == 204
    # Gone.
    assert client.get(f"/api/projects/{project.id}").status_code == 404


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------

def test_list_batches(client, project, batch):
    resp = client.get(f"/api/projects/{project.id}/batches")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "test_batch"


def test_create_batch(client, project):
    resp = client.post(
        f"/api/projects/{project.id}/batches",
        json={"name": "b2", "source_folder_path": "/tmp/b2"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "b2"
    assert data["state"] == "queued"


def test_create_batch_auto_scans_folder(client, project, tmp_path):
    """Creating a batch with an existing folder auto-scans it into ImageItems."""
    (tmp_path / "a.png").write_bytes(b"\x89PNG")
    (tmp_path / "b.jpg").write_bytes(b"\xff\xd8")
    (tmp_path / "notes.txt").write_text("ignored")

    resp = client.post(
        f"/api/projects/{project.id}/batches",
        json={"name": "scanned", "source_folder_path": str(tmp_path)},
    )
    assert resp.status_code == 201
    batch_id = resp.json()["id"]

    # Two images discovered, the .txt ignored.
    items = client.get(f"/api/batches/{batch_id}/items").json()
    assert len(items) == 2
    assert {i["file_name"] for i in items} == {"a.png", "b.jpg"}


def test_scan_removes_deleted_images_from_db(client, project, tmp_path):
    """Re-scanning removes DB rows for image files deleted from disk."""
    img_a = tmp_path / "a.png"
    img_b = tmp_path / "b.png"
    img_a.write_bytes(b"\x89PNG")
    img_b.write_bytes(b"\x89PNG")

    resp = client.post(
        f"/api/projects/{project.id}/batches",
        json={"name": "del-test", "source_folder_path": str(tmp_path)},
    )
    assert resp.status_code == 201
    batch_id = resp.json()["id"]
    assert len(client.get(f"/api/batches/{batch_id}/items").json()) == 2

    # Delete one image from disk and rescan.
    img_b.unlink()
    resp = client.post(f"/api/batches/{batch_id}/scan")
    assert resp.status_code == 200

    items = client.get(f"/api/batches/{batch_id}/items").json()
    assert len(items) == 1
    assert items[0]["file_name"] == "a.png"


def test_scan_removes_sidecar_json_for_deleted_image(client, project, tmp_path):
    """Re-scanning also deletes the JSON sidecar next to a removed image."""
    img = tmp_path / "x.png"
    sidecar = tmp_path / "x.json"
    img.write_bytes(b"\x89PNG")
    sidecar.write_text('{"prompt": "test"}')

    resp = client.post(
        f"/api/projects/{project.id}/batches",
        json={"name": "sidecar-test", "source_folder_path": str(tmp_path)},
    )
    batch_id = resp.json()["id"]

    img.unlink()
    client.post(f"/api/batches/{batch_id}/scan")

    assert not sidecar.exists(), "Sidecar JSON should be deleted along with the image item"
    assert client.get(f"/api/batches/{batch_id}/items").json() == []


def test_create_batch_missing_folder_is_non_fatal(client, project):
    """A missing source folder doesn't block creation — batch is created empty."""
    resp = client.post(
        f"/api/projects/{project.id}/batches",
        json={"name": "nofolder", "source_folder_path": "/__no_such_dir__/x"},
    )
    assert resp.status_code == 201
    batch_id = resp.json()["id"]
    assert client.get(f"/api/batches/{batch_id}/items").json() == []


def test_get_batch(client, batch):
    resp = client.get(f"/api/batches/{batch.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test_batch"


def test_update_batch(client, batch):
    resp = client.patch(f"/api/batches/{batch.id}", json={"name": "updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated"


def test_delete_batch(client, batch):
    resp = client.delete(f"/api/batches/{batch.id}")
    assert resp.status_code == 204


def test_batch_lifecycle_pause_resume(client, api_session, batch):
    # Move to PROCESSING first.
    batch.state = BatchState.PROCESSING
    api_session.flush()
    resp = client.post(f"/api/batches/{batch.id}/pause")
    assert resp.status_code == 200
    assert resp.json()["state"] == "paused"

    resp = client.post(f"/api/batches/{batch.id}/resume")
    assert resp.status_code == 200
    assert resp.json()["state"] == "queued"


def test_batch_abort(client, api_session, batch):
    batch.state = BatchState.PROCESSING
    api_session.flush()
    resp = client.post(f"/api/batches/{batch.id}/abort")
    assert resp.status_code == 200
    assert resp.json()["state"] == "error"


def test_batch_invalid_transition(client, api_session, batch):
    # DONE has no outgoing transitions.
    batch.state = BatchState.DONE
    api_session.flush()
    resp = client.post(f"/api/batches/{batch.id}/pause")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

def test_list_items(client, batch, item):
    resp = client.get(f"/api/batches/{batch.id}/items")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "img.png"


def test_get_item(client, item):
    resp = client.get(f"/api/items/{item.id}")
    assert resp.status_code == 200
    assert resp.json()["file_name"] == "img.png"


def test_decide_item_accept(client, item):
    resp = client.post(
        f"/api/items/{item.id}/decide",
        json={"decision": "accept"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "approved"
    assert data["decision"] == "accept"


def test_decide_item_accept_sets_final_caption(client, item):
    """Accepting an item copies normalized_caption to final_caption."""
    resp = client.post(f"/api/items/{item.id}/decide", json={"decision": "accept"})
    assert resp.status_code == 200
    # item fixture has normalized_caption="mychar01, portrait"
    assert resp.json()["final_caption"] == "mychar01, portrait"


def test_decide_item_accept_with_custom_caption(client, item):
    """Accepting with an explicit caption stores that caption as final_caption."""
    custom = "mychar01, portrait, custom user edit"
    resp = client.post(
        f"/api/items/{item.id}/decide",
        json={"decision": "accept", "caption": custom},
    )
    assert resp.status_code == 200
    assert resp.json()["final_caption"] == custom


def test_mass_decide_accept_sets_final_caption(client, api_session, batch, item):
    """Mass-accept sets final_caption = normalized_caption for each item."""
    resp = client.post(
        f"/api/batches/{batch.id}/items/mass-decide",
        json={"decision": "accept", "item_ids": [item.id], "include_with_warnings": True},
    )
    assert resp.status_code == 200
    assert resp.json()["applied"] == 1
    # Verify via item endpoint.
    data = client.get(f"/api/items/{item.id}").json()
    assert data["final_caption"] == "mychar01, portrait"


def test_decide_item_drop(client, item):
    resp = client.post(f"/api/items/{item.id}/decide", json={"decision": "drop"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "dropped"


def test_decide_item_regenerate(client, item):
    resp = client.post(f"/api/items/{item.id}/decide", json={"decision": "regenerate"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "queued"
    # Caption should be cleared.
    assert data["normalized_caption"] is None


def test_mass_decide(client, api_session, batch, item):
    # Create second item.
    item2 = ImageItem(
        batch_id=batch.id, file_path="/tmp/src/img2.png",
        file_name="img2.png", state=ItemState.AWAITING_REVIEW,
    )
    api_session.add(item2)
    api_session.flush()

    resp = client.post(
        f"/api/batches/{batch.id}/items/mass-decide",
        json={"decision": "accept", "item_ids": [item.id, item2.id]},
    )
    assert resp.status_code == 200
    assert resp.json()["applied"] == 2


def test_mass_decide_excludes_warnings_by_default(client, api_session, batch, item):
    item.warnings = [{"code": "TRIGGER_MISSING", "message": "x", "source": "rule_checker"}]
    api_session.flush()
    item2 = ImageItem(
        batch_id=batch.id, file_path="/tmp/src/img3.png",
        file_name="img3.png", state=ItemState.AWAITING_REVIEW,
    )
    api_session.add(item2)
    api_session.flush()
    # Without include_with_warnings, item (has warning) should be skipped, item2 accepted.
    resp = client.post(
        f"/api/batches/{batch.id}/items/mass-decide",
        json={"decision": "accept", "item_ids": [item.id, item2.id], "include_with_warnings": False},
    )
    assert resp.json()["applied"] == 1  # only item2


# ---------------------------------------------------------------------------
# Image endpoint: must force revalidation (IDs reuse after batch delete)
# ---------------------------------------------------------------------------

def test_serve_image_sets_no_cache(client, api_session, batch, tmp_path):
    """/api/items/{id}/image must return Cache-Control: no-cache so the browser
    revalidates via ETag. Otherwise reused item IDs (SQLite has no AUTOINCREMENT
    by default) would serve stale icons from a previous batch under the same URL.
    """
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    it = ImageItem(
        batch_id=batch.id, file_path=str(img), file_name="test.png",
        state=ItemState.AWAITING_REVIEW,
    )
    api_session.add(it)
    api_session.commit()

    resp = client.get(f"/api/items/{it.id}/image")
    assert resp.status_code == 200
    assert "no-cache" in resp.headers.get("cache-control", "").lower()


# ---------------------------------------------------------------------------
# Export guard: must not finalize a batch with un-reviewed items
# ---------------------------------------------------------------------------

def test_export_blocked_when_items_awaiting_review(client, api_session, batch, item):
    """Export must be refused (and batch left in AWAITING_REVIEW) while an item
    is still pending review — otherwise the batch would go DONE with un-reviewed
    items and nothing exported."""
    batch.state = BatchState.AWAITING_REVIEW
    api_session.commit()  # persist so a 400-triggered rollback can't wipe the fixture

    resp = client.post(f"/api/batches/{batch.id}/export")
    assert resp.status_code == 400
    assert "pending" in resp.json()["detail"].lower()

    # Batch must remain AWAITING_REVIEW (re-fetch fresh, not via the rolled-back object).
    assert client.get(f"/api/batches/{batch.id}").json()["state"] == "awaiting_review"


def test_export_succeeds_when_all_items_decided(client, api_session, batch, item):
    """With every item decided (here: APPROVED), export writes captions and the
    batch transitions to DONE."""
    import tempfile, os
    # Point the item at a real temp file so the exporter can write a sidecar.
    tmpdir = tempfile.mkdtemp()
    img = os.path.join(tmpdir, "img.png")
    with open(img, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
    batch.state = BatchState.AWAITING_REVIEW
    item.state = ItemState.APPROVED
    item.file_path = img
    item.final_caption = "mychar01, portrait"
    api_session.flush()

    resp = client.post(f"/api/batches/{batch.id}/export")
    assert resp.status_code == 200
    assert resp.json()["state"] == "done"
    assert os.path.exists(os.path.join(tmpdir, "img.txt"))


# ---------------------------------------------------------------------------
# Filesystem browser (folder picker)
# ---------------------------------------------------------------------------

def test_fs_list_existing_dir(client, tmp_path):
    """/api/fs/list returns subdirectories and image count for a real directory."""
    (tmp_path / "sub_a").mkdir()
    (tmp_path / "sub_b").mkdir()
    (tmp_path / "img1.png").write_bytes(b"\x89PNG")
    (tmp_path / "notes.txt").write_text("x")

    resp = client.get(f"/api/fs/list?path={tmp_path}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    names = sorted(d["name"] for d in data["dirs"])
    assert names == ["sub_a", "sub_b"]
    assert data["image_count"] == 1  # only the .png counts
    assert data["parent"] is not None


def test_fs_list_nonexistent_returns_error_field(client):
    """Nonexistent path: 200 with error message (not HTTP 5xx)."""
    resp = client.get("/api/fs/list?path=/__definitely_does_not_exist__/x")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"]
    assert data["dirs"] == []


def test_fs_list_empty_path_returns_start_point(client):
    """Empty path: drives on Windows, root listing on POSIX. Either way, no error."""
    resp = client.get("/api/fs/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    # Either drives or some root entries are returned.
    assert isinstance(data["dirs"], list)


# ---------------------------------------------------------------------------
# State-history sort tolerates mixed naive/aware datetimes
# ---------------------------------------------------------------------------

def test_history_sort_key_handles_mixed_tz_datetimes():
    """sorted() over state history must not raise on a mix of naive and aware
    datetimes (regression: a manually-edited aware row crashed batch_form)."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from caption_agent.api.stats import _history_sort_key

    rows = [
        SimpleNamespace(changed_at=datetime(2026, 5, 29, 20, 0, 13)),  # naive
        SimpleNamespace(changed_at=datetime(2026, 5, 27, 20, 0, 0, tzinfo=timezone.utc)),  # aware
        SimpleNamespace(changed_at=None),
    ]
    # Must not raise, and the None sorts first, aware (earlier) before naive (later).
    ordered = sorted(rows, key=_history_sort_key)
    assert ordered[0].changed_at is None
    assert ordered[1].changed_at.tzinfo is not None
    assert ordered[2].changed_at.tzinfo is None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_get_all_config(client, api_session):
    from caption_agent.config.manager import ConfigManager
    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert "llm" in resp.json()


def test_get_config_key(client, api_session):
    from caption_agent.config.manager import ConfigManager
    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    resp = client.get("/api/config/llm")
    assert resp.status_code == 200
    assert resp.json()["key"] == "llm"


def test_patch_config(client, api_session):
    from caption_agent.config.manager import ConfigManager
    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    resp = client.patch("/api/config/retry", json={"value": {"normalizer_max_self_retries": 5}})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# S1: LLM connection test endpoint
# ---------------------------------------------------------------------------

def test_llm_test_success(client, api_session):
    """POST /api/config/llm/test returns {ok, model_id, latency_ms} when LLM responds."""
    from caption_agent.config.manager import ConfigManager
    from unittest.mock import patch

    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    with patch("caption_agent.api.config.LLMClient") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.chat.return_value = "ok"
        resp = client.post("/api/config/llm/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "model_id" in data
    assert "latency_ms" in data


def test_llm_test_failure(client, api_session):
    """POST /api/config/llm/test returns {ok: false, error} when LLM is unreachable."""
    from caption_agent.config.manager import ConfigManager
    from caption_agent.llm.client import LLMTransientError
    from unittest.mock import patch

    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    with patch("caption_agent.api.config.LLMClient") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.chat.side_effect = LLMTransientError("Connection refused")
        resp = client.post("/api/config/llm/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "Connection refused" in data["error"]


def test_llm_test_per_step(client, api_session):
    """POST /api/config/llm/test?step=analyst tests the analyst step config."""
    from caption_agent.config.manager import ConfigManager
    from unittest.mock import patch

    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    with patch("caption_agent.api.config.LLMClient") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.chat.return_value = "ok"
        resp = client.post("/api/config/llm/test?step=analyst")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# S2: log level selector — PATCH logging applies level immediately
# ---------------------------------------------------------------------------

def test_patch_logging_applies_log_level(client, api_session):
    """PATCH /api/config/logging with log_level calls set_log_level immediately."""
    from caption_agent.config.manager import ConfigManager
    from unittest.mock import patch

    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    with patch("caption_agent.api.config.set_log_level") as mock_set:
        resp = client.patch(
            "/api/config/logging",
            json={"value": {"log_level": "DEBUG", "business_log_retention_days": 30,
                            "debug_dump_llm_io": False}},
        )

    assert resp.status_code == 200
    mock_set.assert_called_once_with("DEBUG")


def test_patch_other_key_does_not_call_set_log_level(client, api_session):
    """PATCH on a non-logging key must NOT call set_log_level."""
    from caption_agent.config.manager import ConfigManager
    from unittest.mock import patch

    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    with patch("caption_agent.api.config.set_log_level") as mock_set:
        client.patch("/api/config/retry", json={"value": {"normalizer_max_self_retries": 5}})

    mock_set.assert_not_called()


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def test_get_logs_empty(client):
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_delete_logs(client, api_session):
    from caption_agent.models import BusinessLog
    from caption_agent.models.enums import LogLevel
    api_session.add(BusinessLog(event_type="test", message="msg", level=LogLevel.INFO))
    api_session.flush()

    resp = client.delete("/api/logs")
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 1
