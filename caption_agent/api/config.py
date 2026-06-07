"""Config GET/PATCH endpoints for the Settings UI (D-090)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config.manager import ConfigManager
from ..config.schema import LoggingConfig
from ..llm.client import LLMClient
from ..logging_setup.system_logger import get_system_logger, set_log_level
from ..schemas.config import ConfigOut, ConfigPatch
from ..storage.session import get_session

router = APIRouter(prefix="/api/config", tags=["config"])

_ALLOWED_KEYS = {
    "llm",
    "llm_analyst",
    "llm_normalizer",
    "llm_checker",
    # llm_gap_filler removed (D-102) — old DBs may still have this key, PATCH is no longer accepted
    "retry",
    "polling",
    "logging",
    "paths",
}


@router.get("", response_model=dict)
def get_all_config(session: Session = Depends(get_session)) -> dict:
    """Return all runtime config as a flat key→value dict."""
    mgr = ConfigManager(session)
    return mgr.all()


@router.get("/{key}", response_model=ConfigOut)
def get_config(key: str, session: Session = Depends(get_session)) -> ConfigOut:
    mgr = ConfigManager(session)
    value = mgr.get(key)
    return ConfigOut(key=key, value=value)


@router.patch("/{key}", response_model=ConfigOut)
def update_config(
    key: str,
    body: ConfigPatch,
    session: Session = Depends(get_session),
) -> ConfigOut:
    mgr = ConfigManager(session)
    mgr.set(key, body.value)
    # Side-effect: apply log_level immediately when logging config is saved.
    if key == "logging" and isinstance(body.value, dict):
        level = body.value.get("log_level")
        if level:
            set_log_level(level)
    return ConfigOut(key=key, value=body.value)


@router.get("/llm/status")
def llm_status(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Return current LLM config info for the nav indicator — no LLM call made.

    Returns ``model_id``, ``base_url``, and ``profile_name`` (if an active profile exists).
    """
    from ..models import LLMProfile  # noqa: PLC0415

    mgr = ConfigManager(session)
    cfg = mgr.get_main_llm()
    active = session.query(LLMProfile).filter(LLMProfile.is_active.is_(True)).first()
    return {
        "model_id": cfg.model_id or "",
        "base_url": cfg.base_url or "",
        "profile_name": active.name if active else None,
    }


@router.post("/llm/test")
def test_llm_connection(
    step: str | None = Query(default=None),
    profile_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Probe the LLM endpoint with a minimal request.

    Args:
        step: one of ``analyst`` / ``normalizer`` / ``checker`` to test a
              per-step override, or omit to test the main LLM config.
        profile_id: if given, test against the profile's snapshot *without activating it*.
                    When combined with ``step``, resolves field-by-field from the profile's
                    main ``llm`` block and the step's override block.

    Returns ``{ok, model_id, latency_ms}`` on success or ``{ok: false, error}``
    on failure (never raises HTTP 5xx — connection errors are part of the result).
    """
    from ..models import LLMProfile
    from ..schemas.llm_profile import LLMProfileSnapshot

    log = get_system_logger()
    mgr = ConfigManager(session)

    if profile_id is not None:
        p = session.get(LLMProfile, profile_id)
        if p is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"LLM profile {profile_id} not found")
        snapshot = LLMProfileSnapshot.model_validate_json(p.config_json)
        target = f"profile '{p.name}'"
        if step and step in ("analyst", "normalizer", "checker"):
            target = f"profile '{p.name}' / step '{step}'"
            # Merge step override on top of profile's main config.
            step_override_raw = getattr(snapshot, f"llm_{step}").model_dump()
            merged_fields = snapshot.llm.model_dump()
            for field_name, value in step_override_raw.items():
                if value is not None:
                    merged_fields[field_name] = value
            from ..config.schema import LLMConfig
            cfg = LLMConfig.model_validate(merged_fields)
        else:
            cfg = snapshot.llm
    else:
        target = f"step '{step}'" if step and step in ("analyst", "normalizer", "checker") else "main LLM"
        if step and step in ("analyst", "normalizer", "checker"):
            cfg = mgr.get_effective_llm_for_step(step)
        else:
            cfg = mgr.get_main_llm()

    from ..config.bootstrap import get_bootstrap_settings  # noqa: PLC0415
    from ..config.schema import LoggingConfig  # noqa: PLC0415
    from ..logging_setup.llm_io_dumper import LLMIODumper  # noqa: PLC0415

    logging_cfg = LoggingConfig.model_validate(mgr.get("logging") or {})
    dump_step = f"test_{(step or 'main').replace(' ', '_')}"
    dumper = LLMIODumper(
        dump_dir=get_bootstrap_settings().llm_io_dir,
        enabled=logging_cfg.debug_dump_llm_io,
    )

    log.info("LLM connection test started for %s (%s @ %s)", target, cfg.model_id, cfg.base_url)
    try:
        with LLMClient(cfg) as client:
            client.set_dump_context(
                dumper=dumper if dumper.is_enabled() else None,
                project_id=0, batch_id=0, item_id=0, step=dump_step,
            )
            start = time.monotonic()
            client.chat([{"role": "user", "content": "Hi"}])
            latency_ms = round((time.monotonic() - start) * 1000)
        log.info("LLM connection test OK for %s — %s, %d ms", target, cfg.model_id, latency_ms)
        return {"ok": True, "model_id": cfg.model_id, "latency_ms": latency_ms}
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM connection test FAILED for %s: %s", target, str(exc)[:300])
        return {"ok": False, "error": str(exc)[:300]}
