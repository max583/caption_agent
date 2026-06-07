"""Pipeline Step 2: Image Analyst (VLM call).

Sends the image to the configured VLM and receives a structured JSON description
of pose, framing, clothing, expression, setting, defects, etc.
Saves the parsed dict to ``ImageItem.raw_analyst_output``.

Raises ``LLMValidationError`` if the response cannot be parsed as JSON — the
batch_processor catches this and retries with a temperature bump.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..llm.client import LLMClient, LLMValidationError
from ..logging_setup.system_logger import get_system_logger
from ..models import ImageItem
from ._prompts import load_prompt


def run(
    item: ImageItem,
    session: Session,  # noqa: ARG001
    client: LLMClient,
    *,
    temperature: float | None = None,
) -> None:
    """Run VLM analysis; update ``item.raw_analyst_output`` in-place."""
    image_path = Path(item.file_path)
    if not image_path.exists():
        from ..llm.client import LLMPermanentError  # noqa: PLC0415

        raise LLMPermanentError(f"Image file not found: {image_path}")

    system_prompt = load_prompt("analyst_vision.txt")
    user_text = _build_user_text(item)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    log = get_system_logger()
    log.debug("[analyst] item %d — sending image to VLM: %s", item.id, item.file_name)

    raw = client.vision(image_path, messages, temperature=temperature)
    result = _parse_response(raw)
    item.raw_analyst_output = result

    if log.isEnabledFor(logging.DEBUG):
        log.debug(
            "[analyst] item %d — result: crop=%s angle=%s expression=%s setting=%s "
            "adult=%s defects=%s other_chars=%s",
            item.id,
            result.get("crop"), result.get("camera_angle"), result.get("expression"),
            result.get("setting"), result.get("adult_context"),
            result.get("defects"), result.get("other_characters"),
        )


def _build_user_text(item: ImageItem) -> str:  # noqa: ARG001  (item reserved for future slots)
    # D-102: analyst works from pixels only; generation_prompt is no longer an input.
    return (
        "Analyze this image.\n"
        "\nReturn JSON with keys: raw_description, pose, camera_angle, crop, "
        "clothing, expression, setting, other_characters (list), adult_context (bool), "
        "defects (list), uncertainty_notes (list)."
    )


def _parse_response(raw: str) -> dict[str, Any]:
    # Strip markdown fences if present.
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("` \n")
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict):
                data.setdefault("raw_description", raw)
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    raise LLMValidationError(f"Analyst returned non-JSON response: {raw[:400]!r}")
