"""Tests for LLMProfile model, ConfigManager snapshot helpers, and the
/api/llm-profiles REST API (CRUD + activate).
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from caption_agent.config.manager import ConfigManager
from caption_agent.config.schema import LLMConfig, StepLLMOverride
from caption_agent.models import Base, Configuration, LLMProfile
from caption_agent.schemas.llm_profile import LLMProfileSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)
    e.dispose()


@pytest.fixture
def session(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionLocal()
    yield s
    s.close()


def _mgr(session: Session) -> ConfigManager:
    mgr = ConfigManager(session)
    mgr.seed_defaults_if_missing()
    session.commit()
    return mgr


# ---------------------------------------------------------------------------
# LLMProfile model
# ---------------------------------------------------------------------------


class TestLLMProfileModel:
    def test_create_profile(self, session: Session) -> None:
        p = LLMProfile(
            name="Ollama local",
            config_json=json.dumps({"llm": {}, "llm_analyst": {}, "llm_normalizer": {}, "llm_checker": {}}),
        )
        session.add(p)
        session.commit()
        assert p.id is not None
        assert p.is_active is False
        assert p.created_at is not None

    def test_name_unique_constraint(self, session: Session) -> None:
        from sqlalchemy.exc import IntegrityError

        session.add(LLMProfile(name="dup", config_json="{}"))
        session.commit()
        session.add(LLMProfile(name="dup", config_json="{}"))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_id_is_monotonically_assigned(self, session: Session) -> None:
        """IDs should be sqlite_autoincrement — never reused."""
        p1 = LLMProfile(name="a", config_json="{}")
        p2 = LLMProfile(name="b", config_json="{}")
        session.add_all([p1, p2])
        session.commit()
        assert p2.id > p1.id

    def test_repr(self, session: Session) -> None:
        p = LLMProfile(name="Test", config_json="{}", is_active=True)
        session.add(p)
        session.commit()
        assert "Test" in repr(p)
        assert "active" in repr(p)


# ---------------------------------------------------------------------------
# snapshot_current_llm
# ---------------------------------------------------------------------------


class TestSnapshotCurrentLlm:
    def test_returns_defaults_when_no_config_modified(self, session: Session) -> None:
        mgr = _mgr(session)
        snap = mgr.snapshot_current_llm()
        assert isinstance(snap, LLMProfileSnapshot)
        assert isinstance(snap.llm, LLMConfig)
        assert isinstance(snap.llm_analyst, StepLLMOverride)

    def test_captures_modified_main_llm(self, session: Session) -> None:
        mgr = _mgr(session)
        mgr.set("llm", {"base_url": "http://myserver/v1", "model_id": "my-model",
                         "api_key": "", "temperature": 0.5, "context_length": 0,
                         "max_tokens": 0, "request_timeout": 600, "max_retries": 4,
                         "max_tool_iterations": 8})
        session.commit()
        snap = mgr.snapshot_current_llm()
        assert snap.llm.base_url == "http://myserver/v1"
        assert snap.llm.model_id == "my-model"
        assert snap.llm.temperature == 0.5

    def test_captures_step_overrides(self, session: Session) -> None:
        mgr = _mgr(session)
        mgr.set("llm_analyst", {"model_id": "analyst-model", "temperature": 0.1,
                                  "base_url": None, "api_key": None, "context_length": None,
                                  "max_tokens": None, "request_timeout": None,
                                  "max_retries": None, "max_tool_iterations": None})
        session.commit()
        snap = mgr.snapshot_current_llm()
        assert snap.llm_analyst.model_id == "analyst-model"
        assert snap.llm_analyst.temperature == 0.1
        assert snap.llm_normalizer.model_id is None  # untouched

    def test_does_not_apply_env_var_override(self, session: Session, monkeypatch) -> None:
        """snapshot_current_llm reads raw DB values, not env-var-overridden values."""
        monkeypatch.setenv("CAPTION_AGENT_LLM_API_KEY", "secret-from-env")
        mgr = _mgr(session)
        snap = mgr.snapshot_current_llm()
        assert snap.llm.api_key == ""  # DB default, not the env var


# ---------------------------------------------------------------------------
# apply_llm_snapshot
# ---------------------------------------------------------------------------


class TestApplyLlmSnapshot:
    def test_round_trip(self, session: Session) -> None:
        mgr = _mgr(session)

        original = mgr.snapshot_current_llm()
        original.llm.base_url = "http://roundtrip/v1"
        original.llm.model_id = "rt-model"
        original.llm_checker.temperature = 0.7

        mgr.apply_llm_snapshot(original)
        session.commit()

        restored = mgr.snapshot_current_llm()
        assert restored.llm.base_url == "http://roundtrip/v1"
        assert restored.llm.model_id == "rt-model"
        assert restored.llm_checker.temperature == 0.7

    def test_apply_overwrites_previous_values(self, session: Session) -> None:
        mgr = _mgr(session)
        mgr.set("llm", {**LLMConfig().model_dump(), "model_id": "old-model"})
        session.commit()

        new_snap = LLMProfileSnapshot()
        new_snap.llm.model_id = "new-model"
        mgr.apply_llm_snapshot(new_snap)
        session.commit()

        assert mgr.get_main_llm().model_id == "new-model"

    def test_apply_writes_all_four_keys(self, session: Session) -> None:
        mgr = _mgr(session)
        snap = mgr.snapshot_current_llm()
        snap.llm_analyst.model_id = "analyst"
        snap.llm_normalizer.model_id = "normalizer"
        snap.llm_checker.model_id = "checker"
        mgr.apply_llm_snapshot(snap)
        session.commit()

        assert mgr.get("llm_analyst")["model_id"] == "analyst"
        assert mgr.get("llm_normalizer")["model_id"] == "normalizer"
        assert mgr.get("llm_checker")["model_id"] == "checker"


# ===========================================================================
# API tests — CRUD + activate (Steps 2 & 3)
# ===========================================================================


from fastapi.testclient import TestClient  # noqa: E402 (after fixtures)

from caption_agent.main import app  # noqa: E402
from caption_agent.storage.session import get_session  # noqa: E402


@pytest.fixture
def api_engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)
    e.dispose()


@pytest.fixture
def api_session(api_engine) -> Session:
    SessionLocal = sessionmaker(bind=api_engine, expire_on_commit=False)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def client(api_session: Session):
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
    _deps.set_queue(BatchQueue())
    # Seed defaults so snapshot_current_llm works
    mgr = ConfigManager(api_session)
    mgr.seed_defaults_if_missing()
    api_session.commit()

    c = TestClient(app, raise_server_exceptions=True)
    yield c
    app.dependency_overrides.clear()


def _make_snapshot_body(model_id: str = "test-model") -> dict:
    return {
        "llm": {"base_url": "http://localhost/v1", "api_key": "", "model_id": model_id,
                 "context_length": 0, "max_tokens": 0, "temperature": 0.2,
                 "request_timeout": 600, "max_retries": 4, "max_tool_iterations": 8},
        "llm_analyst": {}, "llm_normalizer": {}, "llm_checker": {},
    }


class TestProfileCRUD:
    def test_list_empty(self, client: TestClient) -> None:
        r = client.get("/api/llm-profiles")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_without_snapshot_snapshots_current(self, client: TestClient) -> None:
        r = client.post("/api/llm-profiles", json={"name": "auto"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "auto"
        assert data["is_active"] is False
        assert "snapshot" in data
        assert "llm" in data["snapshot"]

    def test_create_with_explicit_snapshot(self, client: TestClient) -> None:
        r = client.post("/api/llm-profiles", json={
            "name": "explicit",
            "snapshot": _make_snapshot_body("explicit-model"),
        })
        assert r.status_code == 201
        assert r.json()["snapshot"]["llm"]["model_id"] == "explicit-model"

    def test_create_duplicate_name_returns_409(self, client: TestClient) -> None:
        client.post("/api/llm-profiles", json={"name": "dup"})
        r = client.post("/api/llm-profiles", json={"name": "dup"})
        assert r.status_code == 409

    def test_list_returns_all_profiles_in_order(self, client: TestClient) -> None:
        client.post("/api/llm-profiles", json={"name": "first"})
        client.post("/api/llm-profiles", json={"name": "second"})
        data = client.get("/api/llm-profiles").json()
        assert [p["name"] for p in data] == ["first", "second"]

    def test_get_by_id(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "get-me"}).json()["id"]
        r = client.get(f"/api/llm-profiles/{pid}")
        assert r.status_code == 200
        assert r.json()["name"] == "get-me"

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/llm-profiles/9999").status_code == 404

    def test_patch_rename(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "old-name"}).json()["id"]
        r = client.patch(f"/api/llm-profiles/{pid}", json={"name": "new-name"})
        assert r.status_code == 200
        assert r.json()["name"] == "new-name"

    def test_patch_description(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "p1"}).json()["id"]
        r = client.patch(f"/api/llm-profiles/{pid}", json={"description": "my note"})
        assert r.status_code == 200
        assert r.json()["description"] == "my note"

    def test_patch_snapshot(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "snap"}).json()["id"]
        new_snap = _make_snapshot_body("patched-model")
        r = client.patch(f"/api/llm-profiles/{pid}", json={"snapshot": new_snap})
        assert r.status_code == 200
        assert r.json()["snapshot"]["llm"]["model_id"] == "patched-model"

    def test_patch_rename_conflict_returns_409(self, client: TestClient) -> None:
        client.post("/api/llm-profiles", json={"name": "taken"})
        pid = client.post("/api/llm-profiles", json={"name": "other"}).json()["id"]
        r = client.patch(f"/api/llm-profiles/{pid}", json={"name": "taken"})
        assert r.status_code == 409

    def test_delete_inactive_profile(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "to-delete"}).json()["id"]
        r = client.delete(f"/api/llm-profiles/{pid}")
        assert r.status_code == 204
        assert client.get(f"/api/llm-profiles/{pid}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        assert client.delete("/api/llm-profiles/9999").status_code == 404


class TestProfileActivate:
    def test_activate_copies_snapshot_to_configuration(
        self, client: TestClient, api_session: Session
    ) -> None:
        snap = _make_snapshot_body("activated-model")
        pid = client.post("/api/llm-profiles", json={"name": "activate-me", "snapshot": snap}).json()["id"]

        r = client.post(f"/api/llm-profiles/{pid}/activate")
        assert r.status_code == 200
        assert r.json()["is_active"] is True

        # The flat configuration should now have the profile's model_id.
        mgr = ConfigManager(api_session)
        assert mgr.get_main_llm().model_id == "activated-model"

    def test_activate_clears_previous_active(self, client: TestClient) -> None:
        pid1 = client.post("/api/llm-profiles", json={"name": "p1"}).json()["id"]
        pid2 = client.post("/api/llm-profiles", json={"name": "p2"}).json()["id"]

        client.post(f"/api/llm-profiles/{pid1}/activate")
        client.post(f"/api/llm-profiles/{pid2}/activate")

        assert client.get(f"/api/llm-profiles/{pid1}").json()["is_active"] is False
        assert client.get(f"/api/llm-profiles/{pid2}").json()["is_active"] is True

    def test_activate_idempotent(self, client: TestClient) -> None:
        """Activating the already-active profile is a no-op (no error)."""
        pid = client.post("/api/llm-profiles", json={"name": "active"}).json()["id"]
        client.post(f"/api/llm-profiles/{pid}/activate")
        r = client.post(f"/api/llm-profiles/{pid}/activate")
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_delete_active_profile_returns_409(self, client: TestClient) -> None:
        pid = client.post("/api/llm-profiles", json={"name": "active-del"}).json()["id"]
        client.post(f"/api/llm-profiles/{pid}/activate")
        r = client.delete(f"/api/llm-profiles/{pid}")
        assert r.status_code == 409

    def test_snapshot_includes_all_step_keys(self, client: TestClient) -> None:
        r = client.post("/api/llm-profiles", json={"name": "step-keys"})
        snap = r.json()["snapshot"]
        assert set(snap.keys()) == {"llm", "llm_analyst", "llm_normalizer", "llm_checker"}


class TestLlmTestWithProfileId:
    """POST /api/config/llm/test?profile_id=N — tests profile without activating."""

    def test_nonexistent_profile_id_returns_404(self, client: TestClient) -> None:
        r = client.post("/api/config/llm/test?profile_id=9999")
        assert r.status_code == 404

    def test_profile_id_does_not_activate_profile(
        self, client: TestClient, api_session: Session
    ) -> None:
        snap = _make_snapshot_body("profile-test-model")
        pid = client.post("/api/llm-profiles", json={"name": "test-only", "snapshot": snap}).json()["id"]

        # The test will fail (no real LLM), but the profile must NOT become active.
        client.post(f"/api/config/llm/test?profile_id={pid}")
        assert client.get(f"/api/llm-profiles/{pid}").json()["is_active"] is False

        # The flat config must also be untouched.
        mgr = ConfigManager(api_session)
        assert mgr.get_main_llm().model_id != "profile-test-model"
