"""Pipeline Step 1: Context Reader (non-LLM).

Extracts embedded ComfyUI PNG metadata and/or an existing .json sidecar.
Populates ``ImageItem.provenance``, ``ImageItem.candidate_prompts``, and
``ImageItem.generation_prompt`` (kept for display only; analyst no longer reads it — D-102).
Creates the sidecar when it is absent and embedded metadata is found.

Per D-087: no LLM call. Step is non-blocking and fast.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..logging_setup.system_logger import get_system_logger
from ..models import ImageItem


def _ensure_project_root() -> None:
    # This file: <root>/scripts/caption_agent/caption_agent/pipeline/context_reader.py
    # tools/ lives at the project root, which is parents[4]:
    #   parents[0]=pipeline, [1]=caption_agent(pkg), [2]=caption_agent(app),
    #   parents[3]=scripts, parents[4]=<project root>
    project_root = Path(__file__).parents[4]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def run(item: ImageItem, session: Session) -> None:  # noqa: ARG001
    """Extract provenance from PNG/sidecar; update item fields in-place.

    Session is accepted for interface consistency but not used directly —
    the caller commits after this function returns.
    """
    log = get_system_logger()
    image_path = Path(item.file_path)
    provenance: dict[str, Any] = {}

    log.debug("[context_reader] item %d — %s", item.id, item.file_name)

    # Prefer existing sidecar.
    sidecar = image_path.with_suffix(".json")
    if sidecar.exists():
        try:
            provenance = json.loads(sidecar.read_text(encoding="utf-8"))
            existing_prompt = provenance.get("positive_prompt_extracted", "")
            log.debug(
                "[context_reader] item %d — sidecar found: %s  |  positive_prompt_extracted: %s",
                item.id, sidecar.name,
                repr(existing_prompt[:80]) if existing_prompt else "(empty)",
            )
        except (json.JSONDecodeError, OSError) as exc:
            log.debug("[context_reader] item %d — sidecar read error (%s), will re-extract", item.id, exc)
            provenance = {}
    else:
        log.debug("[context_reader] item %d — no sidecar at %s", item.id, sidecar.name)

    # Fall back to embedded PNG metadata when sidecar is missing / empty.
    if not provenance and image_path.exists() and image_path.suffix.lower() == ".png":
        log.debug("[context_reader] item %d — attempting PNG metadata extraction", item.id)
        _ensure_project_root()
        try:
            from tools.extract_image_metadata import extract_generation_metadata  # noqa: PLC0415

            provenance = extract_generation_metadata(image_path)
            has_prompt = provenance.get("has_comfyui_prompt", False)
            has_workflow = provenance.get("has_comfyui_workflow", False)
            extracted = provenance.get("positive_prompt_extracted", "")
            api_text = provenance.get("api_prompt_text_extracted", "")
            wf_nodes = provenance.get("workflow_text_nodes", [])
            log.debug(
                "[context_reader] item %d — PNG extraction done: "
                "has_prompt=%s has_workflow=%s  "
                "api_prompt_text: %s  "
                "workflow_text_nodes: %d  "
                "positive_prompt_extracted: %s",
                item.id, has_prompt, has_workflow,
                repr(api_text[:80]) if api_text else "(empty)",
                len(wf_nodes),
                repr(extracted[:120]) if extracted else "(empty)",
            )
            # Write sidecar so subsequent runs skip extraction.
            if provenance and not sidecar.exists():
                sidecar.write_text(
                    json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                log.debug("[context_reader] item %d — wrote sidecar %s", item.id, sidecar.name)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "context_reader: metadata extraction failed for %s: %s", image_path, exc
            )
            provenance = {}
    elif not provenance:
        if not image_path.exists():
            log.debug("[context_reader] item %d — image file not found: %s", item.id, image_path)
        elif image_path.suffix.lower() != ".png":
            log.debug("[context_reader] item %d — non-PNG (%s), skipping extraction", item.id, image_path.suffix)

    # generation_prompt kept for UI display only — analyst no longer reads it (D-102).
    generation_prompt: str | None = (
        provenance.get("positive_prompt_extracted") or item.generation_prompt
    )

    log.debug(
        "[context_reader] item %d — final generation_prompt (display only): %s",
        item.id,
        repr(generation_prompt[:100]) if generation_prompt else "(None)",
    )

    item.generation_prompt = generation_prompt
    item.provenance = provenance or None

    # Collect all candidate prompt texts for human reference at review time (D-102).
    _ensure_project_root()
    try:
        from tools.extract_image_metadata import extract_candidate_prompts  # noqa: PLC0415

        item.candidate_prompts = extract_candidate_prompts(provenance) if provenance else []
        log.debug(
            "[context_reader] item %d — candidate_prompts: %d candidate(s)",
            item.id, len(item.candidate_prompts),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("context_reader: extract_candidate_prompts failed for item %d: %s", item.id, exc)
        item.candidate_prompts = []
