"""OpenAI-compatible LLM/VLM client (D-088).

Supports text (chat completions) and vision (base64 image injected into user message).
HTTP-level transient errors are retried automatically with exponential back-off.
Callers catch LLMValidationError for invalid-JSON responses and retry with a
temperature bump at the application layer.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx

from ..config.schema import LLMConfig
from ..logging_setup.llm_io_dumper import LLMIODumper
from ..logging_setup.system_logger import get_system_logger

_PREVIEW_MAX_LINES = 6
_PREVIEW_MAX_CHARS = 600


class LLMError(Exception):
    """Base class for all LLM client errors."""


class LLMTransientError(LLMError):
    """Network failure, 5xx, 429 rate-limit — safe to retry."""


class LLMPermanentError(LLMError):
    """4xx client error (not 429), bad auth — do not retry."""


class LLMValidationError(LLMTransientError):
    """LLM returned malformed / non-JSON output — retry with temperature bump."""


# Known thinking/reasoning model name fragments.  These models use part of the
# token budget for an internal chain-of-thought pass; setting max_tokens too low
# causes content=null because the thinking phase exhausts the budget before the
# visible response begins.
_THINKING_MODEL_PATTERNS: tuple[str, ...] = (
    "qwen3",
    "deepseek-r1",
    "deepseek-r2",
    "/r1",
    "/r2",
    "-thinking",
    ":thinking",
)


def is_thinking_model(model_id: str) -> bool:
    """Return True if model_id matches a known thinking/reasoning model pattern."""
    mid = model_id.lower()
    return any(p in mid for p in _THINKING_MODEL_PATTERNS)


_MIME_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class LLMClient:
    """Synchronous OpenAI-compatible HTTP client.

    One instance per step (or shared across steps when config is identical).
    Always close via context manager or explicit .close() when done.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._http = httpx.Client(headers=headers, timeout=config.request_timeout)
        # Optional dump context — set via set_dump_context() before each step.
        self._dumper: LLMIODumper | None = None
        self._dump_project_id: int = 0
        self._dump_batch_id: int = 0
        self._dump_item_id: int = 0
        self._dump_step: str = ""

    def set_dump_context(
        self, *, dumper: LLMIODumper | None, project_id: int, batch_id: int, item_id: int, step: str
    ) -> None:
        """Configure file-based I/O dumping for the next LLM call(s).

        Call before invoking a pipeline step; call with dumper=None to clear.
        """
        self._dumper = dumper
        self._dump_project_id = project_id
        self._dump_batch_id = batch_id
        self._dump_item_id = item_id
        self._dump_step = step

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> LLMClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ---- Public API ----

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a text chat-completions request; return the assistant content string."""
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens)
        return self._post_with_retry(payload)

    def vision(
        self,
        image_path: Path,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a vision request with the image base64-encoded in the first user message."""
        data_url = _encode_image_as_data_url(image_path)
        messages_with_image = _inject_image(messages, data_url)
        payload = self._build_payload(
            messages_with_image, temperature=temperature, max_tokens=max_tokens
        )
        return self._post_with_retry(payload)

    # ---- Internals ----

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        cfg = self._config
        payload: dict[str, Any] = {
            "model": cfg.model_id,
            "messages": messages,
            "temperature": temperature if temperature is not None else cfg.temperature,
        }
        effective_max = max_tokens if max_tokens is not None else cfg.max_tokens
        if effective_max and effective_max > 0:
            payload["max_tokens"] = effective_max
        return payload

    def _post_with_retry(self, payload: dict[str, Any]) -> str:
        max_retries = self._config.max_retries
        last_exc: LLMTransientError | None = None
        for attempt in range(max_retries + 1):
            try:
                return self._post(payload)
            except LLMTransientError as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(min(2**attempt, 30))
            except LLMPermanentError:
                raise
        raise last_exc  # type: ignore[misc]

    def _post(self, payload: dict[str, Any]) -> str:
        url = self._base_url + "/chat/completions"
        messages: list[dict[str, Any]] = payload.get("messages", [])

        log = get_system_logger()
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "LLM request → %s | model=%s temp=%s\n%s",
                url,
                payload.get("model"),
                payload.get("temperature"),
                _preview_messages(messages),
            )

        t_start = time.monotonic()
        http_error: str | None = None
        try:
            response = self._http.post(url, json=payload)
        except httpx.TimeoutException as exc:
            http_error = f"Request timed out: {exc}"
            raise LLMTransientError(http_error) from exc
        except httpx.NetworkError as exc:
            http_error = f"Network error: {exc}"
            raise LLMTransientError(http_error) from exc
        except httpx.HTTPError as exc:
            http_error = f"HTTP error: {exc}"
            raise LLMTransientError(http_error) from exc
        finally:
            if http_error and self._dumper:
                self._dumper.dump(
                    project_id=self._dump_project_id,
                    batch_id=self._dump_batch_id,
                    item_id=self._dump_item_id,
                    step=self._dump_step,
                    request_messages=_strip_images_for_dump(messages),
                    response_text=None,
                    error=http_error,
                    latency_ms=(time.monotonic() - t_start) * 1000,
                )

        if response.status_code == 429:
            raise LLMTransientError(f"Rate limited (429): {response.text[:200]}")
        if response.status_code >= 500:
            raise LLMTransientError(
                f"Server error ({response.status_code}): {response.text[:200]}"
            )
        if response.status_code >= 400:
            raise LLMPermanentError(
                f"Client error ({response.status_code}): {response.text[:200]}"
            )

        latency_ms = (time.monotonic() - t_start) * 1000
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if content is None:
                diagnostic = _summarize_null_content_response(data, payload)
                log.warning("LLM returned content=null | %s", diagnostic)
                if self._dumper:
                    self._dumper.dump(
                        project_id=self._dump_project_id,
                        batch_id=self._dump_batch_id,
                        item_id=self._dump_item_id,
                        step=self._dump_step,
                        request_messages=_strip_images_for_dump(messages),
                        response_text=None,
                        error=f"content=null | {diagnostic}",
                        latency_ms=latency_ms,
                    )
                # Thinking models (Qwen3, DeepSeek-R1) can return content=null when
                # max_tokens is exhausted by the thinking phase before any visible
                # output is generated. The diagnostic above keeps the raw failure
                # inspectable without exposing prompt text or image payloads.
                raise LLMPermanentError(
                    "Response content is null — thinking model likely exhausted "
                    "max_tokens in the thinking phase. Remove max_tokens limit or "
                    "increase it significantly (≥512) in the LLM config."
                )
            if not isinstance(content, str):
                raise LLMValidationError(f"Unexpected content type: {type(content)!r}")
            # Strip <think>...</think> blocks produced by reasoning/thinking models
            # (e.g. Qwen3, DeepSeek-R1) — these appear inline in the content field.
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if not content:
                raise LLMValidationError(
                    "Response content was empty after stripping thinking blocks"
                )
            if log.isEnabledFor(logging.DEBUG):
                usage = data.get("usage") or {}
                log.debug(
                    "LLM response ← model=%s | tokens(prompt/completion)=%s/%s\n%s",
                    payload.get("model"),
                    usage.get("prompt_tokens", "?"),
                    usage.get("completion_tokens", "?"),
                    _preview_text(content),
                )
            if self._dumper:
                self._dumper.dump(
                    project_id=self._dump_project_id,
                    batch_id=self._dump_batch_id,
                    item_id=self._dump_item_id,
                    step=self._dump_step,
                    request_messages=_strip_images_for_dump(messages),
                    response_text=content,
                    latency_ms=latency_ms,
                )
            return content
        except LLMValidationError:
            raise
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LLMValidationError(f"Unexpected response shape: {exc}") from exc


# ---- Helpers ----


def _preview_text(text: str, *, max_lines: int = _PREVIEW_MAX_LINES, max_chars: int = _PREVIEW_MAX_CHARS) -> str:
    """Return the first few lines of `text`, truncated, for DEBUG logging.

    Collapses to at most `max_lines` lines and `max_chars` characters; appends an
    ellipsis marker when content was cut.
    """
    if not text:
        return "(empty)"
    lines = text.splitlines()
    clipped_lines = lines[:max_lines]
    preview = "\n".join(clipped_lines)
    truncated = len(lines) > max_lines
    if len(preview) > max_chars:
        preview = preview[:max_chars]
        truncated = True
    return preview + (" …[truncated]" if truncated else "")


def _summarize_null_content_response(data: dict[str, Any], payload: dict[str, Any]) -> str:
    """Return a safe one-line diagnostic for responses with message.content=null.

    The summary excludes request messages, image data, API keys, and raw reasoning
    text. It keeps enough response shape to distinguish token-budget exhaustion
    from endpoint/model quirks.
    """
    choice = (data.get("choices") or [{}])[0] or {}
    message = choice.get("message") or {}
    usage = data.get("usage") or {}
    reasoning = message.get("reasoning_content")
    refusal = message.get("refusal")
    tool_calls = message.get("tool_calls")
    summary = {
        "model": payload.get("model"),
        "payload_has_max_tokens": "max_tokens" in payload,
        "payload_max_tokens": payload.get("max_tokens"),
        "finish_reason": choice.get("finish_reason"),
        "message_keys": sorted(message.keys()) if isinstance(message, dict) else [],
        "role": message.get("role") if isinstance(message, dict) else None,
        "reasoning_content_present": isinstance(reasoning, str) and bool(reasoning.strip()),
        "reasoning_content_chars": len(reasoning) if isinstance(reasoning, str) else None,
        "refusal_preview": _preview_text(refusal, max_lines=1, max_chars=160)
        if isinstance(refusal, str) and refusal
        else None,
        "tool_calls_count": len(tool_calls) if isinstance(tool_calls, list) else None,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    }
    return json.dumps(summary, ensure_ascii=True, sort_keys=True)


def _preview_messages(messages: list[dict[str, Any]]) -> str:
    """Render a compact, base64-free preview of chat messages for DEBUG logging.

    Image parts in vision messages are replaced with an ``[image]`` placeholder so
    raw base64 never reaches the log.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, str):
            text = content
        else:
            # List content (vision): keep text parts, mark images.
            chunks: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    chunks.append(str(item.get("text", "")))
                elif item.get("type") == "image_url":
                    chunks.append("[image]")
            text = " ".join(chunks)
        parts.append(f"[{role}] {_preview_text(text)}")
    return "\n".join(parts)


def _strip_images_for_dump(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return messages with base64 image_url payloads replaced by a short marker.

    The full prompt text is preserved; only the binary image data is removed so
    dump files stay human-readable and don't balloon to megabytes.
    """
    result: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            stripped: list[dict[str, Any]] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    stripped.append({"type": "image_url", "image_url": {"url": "[image — base64 omitted]"}})
                else:
                    stripped.append(part)
            result.append({**msg, "content": stripped})
        else:
            result.append(msg)
    return result


def _encode_image_as_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = _MIME_MAP.get(suffix)
    if mime is None:
        raise LLMPermanentError(
            f"Unsupported image format {suffix!r}. Supported: {sorted(_MIME_MAP)}"
        )
    with path.open("rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _inject_image(
    messages: list[dict[str, Any]], data_url: str
) -> list[dict[str, Any]]:
    """Return a copy of messages with the image URL injected into the first user message."""
    result: list[dict[str, Any]] = []
    injected = False
    for msg in messages:
        if not injected and msg.get("role") == "user":
            original = msg.get("content", "")
            if isinstance(original, str):
                new_content: list[dict[str, Any]] = [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": original},
                ]
            else:
                new_content = [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    *original,
                ]
            result.append({**msg, "content": new_content})
            injected = True
        else:
            result.append(msg)
    if not injected:
        result.append({
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": data_url}}],
        })
    return result
