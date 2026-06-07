"""Debug-mode LLM I/O file dumper (D-087).

Activated when ``debug_dump_llm_io = true`` in LoggingConfig (or log level is DEBUG).
Writes two plain-text files per LLM call to ``<data_dir>/logs/llm_io/``:

  YYYYMMDD_HHMMSS_item{id}_{step}_req.txt   — full prompt (all messages)
  YYYYMMDD_HHMMSS_item{id}_{step}_resp.txt  — model response + latency

Files are human-readable so they can be opened directly without a JSON viewer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LLMIODumper:
    """Writes one request file + one response file per LLM call when enabled."""

    def __init__(self, *, dump_dir: Path, enabled: bool) -> None:
        self._dir = dump_dir
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def dump(
        self,
        *,
        project_id: int,
        batch_id: int,
        item_id: int,
        step: str,
        request_messages: list[dict[str, Any]],
        response_text: str | None,
        error: str | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """Write request and response to separate txt files.

        Call after a completed LLM exchange (success or error).
        On error, ``response_text`` may be None and ``error`` carries the message.
        """
        if not self._enabled:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stem = f"{ts}_p{project_id}_b{batch_id}_item{item_id}_{step}"

        # --- request file ---
        req_lines: list[str] = [
            f"project_id: {project_id}",
            f"batch_id:   {batch_id}",
            f"item_id:    {item_id}",
            f"step:       {step}",
            f"timestamp:  {ts}",
            "",
        ]
        for msg in request_messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Vision message: keep text parts, mark images.
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif part.get("type") == "image_url":
                            parts.append("[image — base64 omitted]")
                content = "\n".join(parts)
            req_lines += [f"{'─' * 60}", f"[{role}]", f"{'─' * 60}", str(content), ""]
        (self._dir / f"{stem}_req.txt").write_text(
            "\n".join(req_lines), encoding="utf-8"
        )

        # --- response file ---
        resp_lines: list[str] = [
            f"project_id: {project_id}",
            f"batch_id:   {batch_id}",
            f"item_id:    {item_id}",
            f"step:       {step}",
            f"timestamp:  {ts}",
            f"latency:    {f'{latency_ms:.0f} ms' if latency_ms is not None else '—'}",
            "",
            f"{'─' * 60}",
        ]
        if error:
            resp_lines += [f"ERROR: {error}"]
        elif response_text is not None:
            resp_lines += [response_text]
        else:
            resp_lines += ["(no response)"]
        (self._dir / f"{stem}_resp.txt").write_text(
            "\n".join(resp_lines), encoding="utf-8"
        )
