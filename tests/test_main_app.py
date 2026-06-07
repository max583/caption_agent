"""Smoke test for the FastAPI app: health endpoint responds.

NOTE: TestClient is used WITHOUT `with`-context — that intentionally skips lifespan
(which would try to open the real DB file). The health endpoint does not touch the DB,
so this is the cleanest test for it. Lifespan-dependent endpoints will be tested in
Phase 3 with an isolated DB.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    from caption_agent.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
