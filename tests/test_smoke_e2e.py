"""End-to-end smoke test: exercises the full pipeline against a real LLM endpoint.

Skipped automatically unless CAPTION_AGENT_SMOKE_LLM_URL is set in the environment.
This test makes real HTTP calls to the configured LLM and is therefore not part of
the normal CI/unit test suite.

Usage:
    # Start LM Studio (or compatible) and then:
    CAPTION_AGENT_SMOKE_LLM_URL=http://localhost:1234/v1 \\
    CAPTION_AGENT_SMOKE_MODEL=qwen3.6-35b-a3b \\
    pytest tests/test_smoke_e2e.py -v -s

Optional env vars:
    CAPTION_AGENT_SMOKE_LLM_URL   Base URL for the OpenAI-compatible endpoint (required).
    CAPTION_AGENT_SMOKE_MODEL     Model ID to use (default: qwen3.6-35b-a3b).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import caption_agent.storage.connection as _conn
from caption_agent.config.manager import ConfigManager
from caption_agent.models import Base, Batch, BatchStateHistory, ImageItem, Project
from caption_agent.models.enums import BatchState, BranchType, ItemState, SourceType
from caption_agent.orchestration.batch_processor import run_batch

pytestmark = pytest.mark.smoke

_SMOKE_URL_VAR = "CAPTION_AGENT_SMOKE_LLM_URL"
_SMOKE_MODEL_VAR = "CAPTION_AGENT_SMOKE_MODEL"
_DEFAULT_MODEL = "qwen3.6-35b-a3b"


# ---------------------------------------------------------------------------
# Fixtures (function-scoped — each smoke test gets a clean DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def smoke_engine():
    """Isolated in-memory engine wired as the global engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    orig_engine = _conn._engine
    orig_maker = _conn._sessionmaker
    _conn._engine = engine
    _conn._sessionmaker = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()
    _conn._engine = orig_engine
    _conn._sessionmaker = orig_maker


@pytest.fixture
def smoke_session(smoke_engine):
    SessionLocal = sessionmaker(bind=smoke_engine, expire_on_commit=False)
    s = SessionLocal()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get(_SMOKE_URL_VAR),
    reason=f"Set {_SMOKE_URL_VAR} to run smoke tests against a real LLM endpoint",
)
def test_smoke_full_pipeline(smoke_session: Session, tmp_path: Path):
    """Full pipeline smoke run: context_reader → analyst (VLM) → normalizer → rule_checker
    → llm_pass_checker → AWAITING_REVIEW.

    The test creates a small gray PNG, writes a sidecar with generation provenance,
    then calls run_batch() without any mocks against the configured LLM endpoint.

    Pass criteria:
    - Batch reaches AWAITING_REVIEW (or ERROR if the LLM produces policy violations).
    - Item is not left in QUEUED or PROCESSING (pipeline ran to completion).
    - If item is AWAITING_REVIEW, normalized_caption must be non-empty.
    """
    llm_url = os.environ[_SMOKE_URL_VAR]
    model_id = os.environ.get(_SMOKE_MODEL_VAR, _DEFAULT_MODEL)

    # ---- Configure LLM endpoint in DB ----
    mgr = ConfigManager(smoke_session)
    mgr.seed_defaults_if_missing()
    smoke_session.commit()
    mgr.set(
        "llm",
        {
            "base_url": llm_url,
            "model_id": model_id,
            "temperature": 0.2,
            "max_tokens": 500,
            "request_timeout": 120,
            "max_retries": 2,
            "api_key": "",
            "context_length": 0,
            "max_tool_iterations": 8,
        },
    )
    smoke_session.commit()

    # ---- Create test image (64×64 px gray rectangle) ----
    img_path = tmp_path / "smoke_img.png"
    _write_minimal_png(img_path)

    # ---- Write sidecar with helpful provenance ----
    sidecar = img_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps({
            "positive_prompt_extracted": (
                "mychar01, portrait, front view, wearing a white shirt, "
                "neutral expression, outdoor daylight, village yard"
            ),
            "source": "smoke_test",
        }),
        encoding="utf-8",
    )

    # ---- Create project → batch → item ----
    project = Project(name="SmokeProject")
    smoke_session.add(project)
    smoke_session.flush()

    batch = Batch(
        project_id=project.id,
        name="smoke_batch",
        source_folder_path=str(tmp_path),
        state=BatchState.QUEUED,
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    smoke_session.add(batch)
    smoke_session.flush()
    smoke_session.add(
        BatchStateHistory(batch_id=batch.id, to_state=BatchState.QUEUED, reason="smoke_test")
    )

    item = ImageItem(
        batch_id=batch.id,
        file_path=str(img_path),
        file_name=img_path.name,
        state=ItemState.QUEUED,
    )
    smoke_session.add(item)
    smoke_session.commit()

    # ---- Run the full pipeline (no mocks) ----
    print(f"\n[smoke] LLM endpoint : {llm_url}")
    print(f"[smoke] Model         : {model_id}")
    print(f"[smoke] Image         : {img_path}")

    run_batch(batch.id)

    # ---- Assertions ----
    smoke_session.expire_all()
    smoke_session.refresh(batch)
    smoke_session.refresh(item)

    print(f"[smoke] Batch state   : {batch.state}")
    print(f"[smoke] Item state    : {item.state}")
    print(f"[smoke] Caption       : {item.normalized_caption!r}")
    if item.last_error_message:
        print(f"[smoke] Error         : {item.last_error_message}")

    assert item.state not in {ItemState.QUEUED, ItemState.PROCESSING}, (
        f"Pipeline did not advance item beyond initial state: {item.state}"
    )
    assert batch.state in {BatchState.AWAITING_REVIEW, BatchState.ERROR}, (
        f"Unexpected batch terminal state: {batch.state}"
    )

    if item.state == ItemState.AWAITING_REVIEW:
        assert item.normalized_caption, "Item is AWAITING_REVIEW but normalized_caption is empty"
        print(f"\n✓ Smoke PASSED — caption: {item.normalized_caption!r}")
    else:
        # ERROR is accepted: it proves the pipeline ran and the LLM was reachable
        # but the caption may have violated policy rules.
        print(f"\n⚠ Smoke completed with item in ERROR state — check caption policy compliance")


# ---------------------------------------------------------------------------
# Helper: write a minimal PNG without external dependencies
# ---------------------------------------------------------------------------


def _write_minimal_png(path: Path) -> None:
    """Write a small (8×8 px) solid-gray PNG using only stdlib.

    Uses the raw PNG byte format directly so the test has no dependency on
    Pillow (even though Pillow is a project dep, keeping smoke deps minimal
    avoids surprising import errors in stripped environments).
    """
    import struct
    import zlib

    width, height = 8, 8
    # Raw image data: one filter byte (0 = None) per row, followed by RGB pixels.
    raw_rows = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))
    compressed = zlib.compress(raw_rows, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
