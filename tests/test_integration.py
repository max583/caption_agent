"""Integration tests for the full caption-agent pipeline.

These tests call run_batch() directly (synchronously, in-thread) with mock LLM
pipeline steps but real DB I/O, state machine transitions, and config/session
wiring — exercising the orchestration layer end-to-end without a live LLM endpoint.

All seven tests share the same StaticPool in-memory SQLite engine so that
session_scope() calls inside run_batch() (which run synchronously in the test
thread) share the same underlying connection as the test fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import caption_agent.storage.connection as _conn
from caption_agent.config.manager import ConfigManager
from caption_agent.models import Base, Batch, BatchStateHistory, ImageItem, Project
from caption_agent.models.enums import BatchState, BranchType, ItemState, SourceType
from caption_agent.orchestration.batch_processor import run_batch
from caption_agent.pipeline.exporter import export_batch


# ---------------------------------------------------------------------------
# Engine / session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def integ_engine():
    """StaticPool in-memory engine wired as the global engine for session_scope().

    Saves and restores the original global engine/sessionmaker so tests remain
    isolated even when run in the same process as other test modules.
    """
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


@pytest.fixture(scope="function")
def integ_session(integ_engine):
    """Session bound to the StaticPool engine.  Used to set up test data."""
    SessionLocal = sessionmaker(bind=integ_engine, expire_on_commit=False)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def project_and_batch(integ_session: Session):
    """Seed default config, create a project and a QUEUED batch; return (project, batch)."""
    ConfigManager(integ_session).seed_defaults_if_missing()

    project = Project(name="IntegProj", trigger_token="mychar01")
    integ_session.add(project)
    integ_session.flush()

    batch = Batch(
        project_id=project.id,
        name="integ_batch",
        source_folder_path="/tmp/integ",
        state=BatchState.QUEUED,
        source_type=SourceType.SYNTHETIC,
        branch=BranchType.IDENTITY,
    )
    integ_session.add(batch)
    integ_session.flush()
    integ_session.add(
        BatchStateHistory(batch_id=batch.id, to_state=BatchState.QUEUED, reason="created")
    )
    integ_session.commit()
    return project, batch


def _add_items(session: Session, batch_id: int, n: int) -> list[ImageItem]:
    """Create n QUEUED ImageItem rows with non-existent file paths."""
    items = [
        ImageItem(
            batch_id=batch_id,
            file_path=f"/tmp/integ/img{i}.png",
            file_name=f"img{i}.png",
            state=ItemState.QUEUED,
        )
        for i in range(n)
    ]
    for item in items:
        session.add(item)
    session.flush()
    session.commit()
    return items


# ---------------------------------------------------------------------------
# Shared mock step implementations
# ---------------------------------------------------------------------------

# A valid analyst output dict.
_ANALYST_OUTPUT: dict = {
    "raw_description": "A person standing in a village yard.",
    "pose": "standing",
    "camera_angle": "front",
    "crop": "fullbody",
    "clothing": "wearing a white T-shirt and jeans",
    "expression": "neutral",
    "setting": "village yard",
    "other_characters": [],
    "adult_context": False,
    "defects": [],
    "uncertainty_notes": [],
}

# Caption that passes all 12 rule_checker rules (SYNTHETIC / IDENTITY branch).
_VALID_CAPTION = (
    "mychar01, fullbody, front view, wearing a white T-shirt and jeans, "
    "neutral expression, outdoor daylight, village yard"
)


def _mock_context_reader(item: ImageItem, session: Session) -> None:
    item.generation_prompt = "mock generation prompt"


def _mock_analyst(item: ImageItem, session: Session, client, **kwargs) -> None:
    item.raw_analyst_output = _ANALYST_OUTPUT


def _mock_normalizer(item: ImageItem, session: Session, client, **kwargs) -> None:
    item.normalized_caption = _VALID_CAPTION



def _mock_llm_pass_checker(item: ImageItem, session: Session, client, **kwargs) -> None:
    item.llm_pass_result = {"ok": True, "warnings": [], "raw_response": "[]"}
    item.warnings = None


# ---------------------------------------------------------------------------
# Test 1: happy path — all items reach AWAITING_REVIEW
# ---------------------------------------------------------------------------


def test_run_batch_happy_path(integ_session: Session, project_and_batch):
    """All pipeline steps succeed: batch → AWAITING_REVIEW, items → AWAITING_REVIEW."""
    _, batch = project_and_batch
    items = _add_items(integ_session, batch.id, 2)

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW

    for item in items:
        integ_session.refresh(item)
        assert item.state == ItemState.AWAITING_REVIEW
        assert item.normalized_caption == _VALID_CAPTION
        assert item.raw_analyst_output == _ANALYST_OUTPUT


# ---------------------------------------------------------------------------
# Test 2: permanent LLM error on item 0 → ERROR; item 1 still succeeds
# ---------------------------------------------------------------------------


def test_run_batch_item_permanent_error(integ_session: Session, project_and_batch):
    """A permanent error on item 0 sets it to ERROR; item 1 proceeds normally."""
    _, batch = project_and_batch
    items = _add_items(integ_session, batch.id, 2)
    call_count = [0]

    def analyst_fails_first(item: ImageItem, session: Session, client, **kwargs) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            from caption_agent.llm.client import LLMPermanentError

            raise LLMPermanentError("Simulated permanent failure on item 0")
        item.raw_analyst_output = _ANALYST_OUTPUT

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_fails_first),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW

    integ_session.refresh(items[0])
    integ_session.refresh(items[1])
    assert items[0].state == ItemState.ERROR
    assert items[0].last_error_category == "permanent"
    assert items[1].state == ItemState.AWAITING_REVIEW


# ---------------------------------------------------------------------------
# Test 3: consecutive failure threshold → batch halted to ERROR
# ---------------------------------------------------------------------------


def test_run_batch_consecutive_failure_threshold(integ_session: Session, project_and_batch):
    """When consecutive failures hit the threshold the batch is moved to ERROR."""
    _, batch = project_and_batch
    # Low threshold so the second failure triggers the halt.
    batch.consecutive_failure_threshold_override = 1
    integ_session.commit()
    _add_items(integ_session, batch.id, 3)

    def analyst_always_fails(item: ImageItem, session: Session, client, **kwargs) -> None:
        from caption_agent.llm.client import LLMPermanentError

        raise LLMPermanentError("Always fails")

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_always_fails),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),
        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.ERROR


# ---------------------------------------------------------------------------
# Test 4: soft-pause mid-batch — second item not processed
# ---------------------------------------------------------------------------


def test_run_batch_soft_pause(integ_session: Session, project_and_batch):
    """Pausing the batch (via DB) inside the first item's processing stops the loop
    before the second item is processed.

    The analyst mock sets batch.state = PAUSED using the *same* session it receives —
    the change is committed when that session_scope context exits (after the analyst
    step finishes).  The FOR loop then detects PAUSED before processing item 1.
    """
    _, batch = project_and_batch
    items = _add_items(integ_session, batch.id, 2)
    batch_id = batch.id
    analyst_calls = [0]

    def analyst_pauses_after_first(item: ImageItem, session: Session, client, **kwargs) -> None:
        item.raw_analyst_output = _ANALYST_OUTPUT
        analyst_calls[0] += 1
        if analyst_calls[0] == 1:
            # Pause via the same open session — committed when session_scope exits.
            b = session.get(Batch, batch_id)
            if b is not None:
                b.state = BatchState.PAUSED

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_pauses_after_first),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.PAUSED, (
        f"Batch should be PAUSED, got {updated_batch.state}"
    )

    integ_session.refresh(items[0])
    integ_session.refresh(items[1])
    # Item 0 completed its pipeline run before the pause check for item 1.
    assert items[0].state == ItemState.AWAITING_REVIEW
    # Item 1 was never processed — still QUEUED.
    assert items[1].state == ItemState.QUEUED


# ---------------------------------------------------------------------------
# Test 5: normalizer self-retry loop (rule violation on attempt 1)
# ---------------------------------------------------------------------------


def test_run_batch_normalizer_retry(integ_session: Session, project_and_batch):
    """The normalizer is retried when rule_checker finds violations on the first attempt."""
    _, batch = project_and_batch
    _add_items(integ_session, batch.id, 1)
    norm_calls = [0]

    def normalizer_fails_first(item: ImageItem, session: Session, client, **kwargs) -> None:
        norm_calls[0] += 1
        if norm_calls[0] == 1:
            # Violates TRIGGER_MISSING: no "mychar01" prefix.
            item.normalized_caption = "portrait, wearing a shirt, outdoor daylight, village yard"
        else:
            # Second attempt: valid caption.
            item.normalized_caption = _VALID_CAPTION

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=normalizer_fails_first),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW
    assert norm_calls[0] == 2, f"Expected exactly 2 normalizer calls, got {norm_calls[0]}"


# ---------------------------------------------------------------------------
# Test 6: context_reader reads provenance from a real sidecar JSON
# ---------------------------------------------------------------------------


def test_run_batch_context_reader_reads_sidecar(
    integ_session: Session, project_and_batch, tmp_path: Path
):
    """context_reader.run() populates item.generation_prompt from a sidecar JSON."""
    _, batch = project_and_batch

    # Minimal valid 1×1 PNG.
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img_path = tmp_path / "sidecar_test.png"
    img_path.write_bytes(png_bytes)

    sidecar_path = img_path.with_suffix(".json")
    sidecar_path.write_text(
        json.dumps({"positive_prompt_extracted": "sidecar test prompt"}),
        encoding="utf-8",
    )

    item = ImageItem(
        batch_id=batch.id,
        file_path=str(img_path),
        file_name="sidecar_test.png",
        state=ItemState.QUEUED,
    )
    integ_session.add(item)
    integ_session.commit()

    # context_reader.run is NOT patched — it reads the real sidecar.
    with (
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    integ_session.refresh(item)

    assert item.state == ItemState.AWAITING_REVIEW
    assert item.generation_prompt == "sidecar test prompt"
    assert item.provenance == {"positive_prompt_extracted": "sidecar test prompt"}


# ---------------------------------------------------------------------------
# Test 7: exporter writes .txt sidecars for APPROVED items
# ---------------------------------------------------------------------------


def test_exporter_writes_txt_sidecars(
    integ_session: Session, project_and_batch, tmp_path: Path
):
    """export_batch() writes a .txt sidecar for each APPROVED item with a final_caption."""
    _, batch = project_and_batch

    captions = [
        "mychar01, portrait, wearing a shirt, neutral, outdoor daylight, village",
        "mychar01, fullbody, wearing jeans, neutral, outdoor daylight, village",
    ]
    img_paths: list[Path] = []

    for i, (state, cap) in enumerate(
        [
            (ItemState.APPROVED, captions[0]),
            (ItemState.APPROVED, captions[1]),
            (ItemState.DROPPED, None),  # should NOT produce a .txt
        ]
    ):
        p = tmp_path / f"img{i}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        img_paths.append(p)
        integ_session.add(
            ImageItem(
                batch_id=batch.id,
                file_path=str(p),
                file_name=p.name,
                state=state,
                normalized_caption=cap,
                final_caption=cap,
            )
        )

    integ_session.commit()

    written = export_batch(batch, integ_session)
    integ_session.commit()

    assert written == 2

    for i, cap in enumerate(captions):
        txt = img_paths[i].with_suffix(".txt")
        assert txt.exists(), f"{txt} not created by exporter"
        assert txt.read_text(encoding="utf-8").strip() == cap

    # Dropped item must not have a .txt.
    assert not img_paths[2].with_suffix(".txt").exists()


# ---------------------------------------------------------------------------
# Test 8: transient LLM error → item re-queued (not ERROR), batch paused
# ---------------------------------------------------------------------------


def test_run_batch_transient_error_requeues_and_pauses(integ_session: Session, project_and_batch):
    """A transient network error re-queues the item instead of setting it to ERROR,
    and pauses the batch when the consecutive-network-failure threshold is reached.

    Contrast with test 3: permanent errors → batch ERROR; transient → batch PAUSED.
    """
    _, batch = project_and_batch
    # threshold=1 so the very first transient failure triggers the pause.
    batch.consecutive_failure_threshold_override = 1
    integ_session.commit()
    items = _add_items(integ_session, batch.id, 2)

    def analyst_always_transient(item: ImageItem, session: Session, client, **kwargs) -> None:
        from caption_agent.llm.client import LLMTransientError
        raise LLMTransientError("Simulated connection refused")

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_always_transient),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),
        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()

    updated_batch = integ_session.get(Batch, batch.id)
    # Batch must be PAUSED (not ERROR) — user can fix the endpoint and resume.
    assert updated_batch.state == BatchState.PAUSED, (
        f"Expected PAUSED, got {updated_batch.state}"
    )

    integ_session.refresh(items[0])
    integ_session.refresh(items[1])
    # Item 0 must be re-queued, not in ERROR — no manual retry needed.
    assert items[0].state == ItemState.QUEUED, (
        f"Expected QUEUED (re-queued), got {items[0].state}"
    )
    # Re-queue must NOT leave a phantom error on the item.
    assert items[0].last_error_message is None
    assert items[0].last_error_category is None
    assert items[0].last_error_at is None
    # Item 1 was never started (batch paused after item 0).
    assert items[1].state == ItemState.QUEUED


# ---------------------------------------------------------------------------
# Test 9: permanent error records a timestamp; recovery clears the error
# ---------------------------------------------------------------------------


def test_error_records_timestamp_and_clears_on_success(integ_session: Session, project_and_batch):
    """A permanent error stamps last_error_at; a later successful run clears all error fields."""
    _, batch = project_and_batch
    items = _add_items(integ_session, batch.id, 1)
    analyst_calls = [0]

    def analyst_fails_then_succeeds(item: ImageItem, session: Session, client, **kwargs) -> None:
        analyst_calls[0] += 1
        if analyst_calls[0] == 1:
            from caption_agent.llm.client import LLMPermanentError
            raise LLMPermanentError("Simulated permanent failure")
        item.raw_analyst_output = _ANALYST_OUTPUT

    # First run: analyst fails → item ERROR with a timestamp.
    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_fails_then_succeeds),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    integ_session.refresh(items[0])
    assert items[0].state == ItemState.ERROR
    assert items[0].last_error_at is not None, "Error must record a timestamp"
    assert items[0].last_error_category == "permanent"

    # User retries the error item → back to QUEUED, then re-run succeeds.
    items[0].state = ItemState.QUEUED
    integ_session.commit()

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=analyst_fails_then_succeeds),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=_mock_llm_pass_checker),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    integ_session.refresh(items[0])
    # Successful completion must clear all stale error fields.
    assert items[0].state == ItemState.AWAITING_REVIEW
    assert items[0].last_error_message is None
    assert items[0].last_error_category is None
    assert items[0].last_error_at is None


# ---------------------------------------------------------------------------
# Tests 10-12: D-097 — LLM-checker warnings drive normalizer self-retry
# ---------------------------------------------------------------------------


_LLM_WARNING = {"source": "llm_pass_checker", "code": "SETTING_OVERSPECIFIC",
                "message": "Setting too specific"}


def test_d097_llm_warnings_trigger_normalizer_retry(integ_session: Session, project_and_batch):
    """LLM-checker violations with attempts remaining → normalizer is retried (D-097).

    Setup: max_retries=1 (2 total attempts).
    Attempt 0: rule_check clean, llm_pass_checker returns a warning → retry.
    Attempt 1: rule_check clean, llm_pass_checker returns clean → AWAITING_REVIEW, no warnings.
    Expected: normalizer called exactly 2 times.
    """
    _, batch = project_and_batch
    ConfigManager(integ_session).set("retry", {
        "normalizer_max_self_retries": 1,
        "consecutive_failure_threshold": 10,
    })
    _add_items(integ_session, batch.id, 1)
    norm_calls = [0]
    checker_calls = [0]

    def counting_normalizer(item: ImageItem, session: Session, client, **kwargs) -> None:
        norm_calls[0] += 1
        item.normalized_caption = _VALID_CAPTION

    def checker_warns_once(item: ImageItem, session: Session, client, **kwargs) -> None:
        checker_calls[0] += 1
        if checker_calls[0] == 1:
            item.warnings = [_LLM_WARNING]
            item.llm_pass_result = {"ok": False, "warnings": [_LLM_WARNING]}
        else:
            item.warnings = None
            item.llm_pass_result = {"ok": True, "warnings": []}

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=counting_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=checker_warns_once),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW
    assert norm_calls[0] == 2, f"Expected 2 normalizer calls, got {norm_calls[0]}"
    assert checker_calls[0] == 2, f"Expected 2 checker calls, got {checker_calls[0]}"

    items = integ_session.query(ImageItem).filter_by(batch_id=batch.id).all()
    assert items[0].state == ItemState.AWAITING_REVIEW
    assert not items[0].warnings, "Warnings should be cleared after clean llm_pass_checker"


def test_d097_llm_warnings_last_attempt_soft_fallback(integ_session: Session, project_and_batch):
    """LLM-checker violations on the last attempt → soft fallback AWAITING_REVIEW (D-097).

    Setup: max_retries=0 (only 1 attempt).
    Attempt 0: rule_check clean, llm_pass_checker always returns a warning.
    Expected: item → AWAITING_REVIEW with the LLM warning visible.
    """
    _, batch = project_and_batch
    ConfigManager(integ_session).set("retry", {
        "normalizer_max_self_retries": 0,
        "consecutive_failure_threshold": 10,
    })
    _add_items(integ_session, batch.id, 1)

    def checker_always_warns(item: ImageItem, session: Session, client, **kwargs) -> None:
        item.warnings = [_LLM_WARNING]
        item.llm_pass_result = {"ok": False, "warnings": [_LLM_WARNING]}

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=_mock_normalizer),

        patch("caption_agent.pipeline.llm_pass_checker.run", side_effect=checker_always_warns),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW

    items = integ_session.query(ImageItem).filter_by(batch_id=batch.id).all()
    assert items[0].state == ItemState.AWAITING_REVIEW, (
        f"Expected AWAITING_REVIEW (soft fallback), got {items[0].state}"
    )
    assert items[0].warnings, "LLM warnings must be surfaced to reviewer on last attempt"
    codes = [w["code"] for w in items[0].warnings]
    assert "SETTING_OVERSPECIFIC" in codes


def test_d097_shared_limit_rule_then_llm_violations(integ_session: Session, project_and_batch):
    """Shared limit: rule violation on attempt 0, LLM violation on attempt 1, clean on 2 (D-097).

    Setup: max_retries=2 (3 total attempts).
    Attempt 0: rule violation → retry.
    Attempt 1: rule clean, LLM warning → retry.
    Attempt 2: rule clean, LLM clean → AWAITING_REVIEW.
    Expected: normalizer called 3 times; item has no warnings.
    """
    _, batch = project_and_batch
    ConfigManager(integ_session).set("retry", {
        "normalizer_max_self_retries": 2,
        "consecutive_failure_threshold": 10,
    })
    _add_items(integ_session, batch.id, 1)
    norm_calls = [0]
    checker_calls = [0]

    def normalizer_bad_then_good(item: ImageItem, session: Session, client, **kwargs) -> None:
        norm_calls[0] += 1
        if norm_calls[0] == 1:
            # Violates TRIGGER_MISSING.
            item.normalized_caption = "portrait, wearing a shirt, outdoor daylight, village yard"
        else:
            item.normalized_caption = _VALID_CAPTION

    def checker_warns_once_then_clean(item: ImageItem, session: Session, client, **kwargs) -> None:
        checker_calls[0] += 1
        if checker_calls[0] == 1:
            item.warnings = [_LLM_WARNING]
            item.llm_pass_result = {"ok": False}
        else:
            item.warnings = None
            item.llm_pass_result = {"ok": True}

    with (
        patch("caption_agent.pipeline.context_reader.run", side_effect=_mock_context_reader),
        patch("caption_agent.pipeline.analyst.run", side_effect=_mock_analyst),
        patch("caption_agent.pipeline.normalizer.run", side_effect=normalizer_bad_then_good),

        patch("caption_agent.pipeline.llm_pass_checker.run",
              side_effect=checker_warns_once_then_clean),
    ):
        run_batch(batch.id)

    integ_session.expire_all()
    updated_batch = integ_session.get(Batch, batch.id)
    assert updated_batch.state == BatchState.AWAITING_REVIEW
    assert norm_calls[0] == 3, f"Expected 3 normalizer calls, got {norm_calls[0]}"
    assert checker_calls[0] == 2, f"Expected 2 checker calls, got {checker_calls[0]}"

    items = integ_session.query(ImageItem).filter_by(batch_id=batch.id).all()
    assert items[0].state == ItemState.AWAITING_REVIEW
    assert not items[0].warnings
