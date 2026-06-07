"""Unit tests for the LLM client (caption_agent/llm/client.py).

All HTTP calls are intercepted via httpx transport mocking — no real LLM endpoint needed.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from caption_agent.config.schema import LLMConfig
from caption_agent.llm.client import (
    LLMClient,
    LLMPermanentError,
    LLMTransientError,
    LLMValidationError,
    _encode_image_as_data_url,
    _inject_image,
    is_thinking_model,
)


# ---- Helpers ----

def _ok_response(content: str = "hello") -> httpx.Response:
    body = json.dumps({
        "choices": [{"message": {"role": "assistant", "content": content}}]
    })
    return httpx.Response(200, text=body, headers={"content-type": "application/json"})


def _null_content_response() -> httpx.Response:
    body = json.dumps({
        "choices": [{
            "finish_reason": "length",
            "message": {
                "role": "assistant",
                "content": None,
                "reasoning_content": "private reasoning should not be logged",
            },
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 512, "total_tokens": 522},
    })
    return httpx.Response(200, text=body, headers={"content-type": "application/json"})


def _error_response(status: int, body: str = "error") -> httpx.Response:
    return httpx.Response(status, text=body)


def _make_client(base_url: str = "http://localhost:1234/v1", max_retries: int = 0) -> LLMClient:
    cfg = LLMConfig(base_url=base_url, api_key="test", max_retries=max_retries)
    return LLMClient(cfg)


class _MockTransport(httpx.BaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = iter(responses)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return next(self._responses)


def _patch_client(client: LLMClient, responses: list[httpx.Response]) -> None:
    client._http = httpx.Client(transport=_MockTransport(responses))


# ---- chat() tests ----

def test_chat_success() -> None:
    client = _make_client()
    _patch_client(client, [_ok_response("caption text")])
    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "caption text"
    client.close()


def test_chat_returns_string_content() -> None:
    client = _make_client()
    _patch_client(client, [_ok_response("mychar01, portrait")])
    assert client.chat([]) == "mychar01, portrait"
    client.close()


def test_chat_raises_permanent_on_4xx() -> None:
    client = _make_client()
    _patch_client(client, [_error_response(401, "Unauthorized")])
    with pytest.raises(LLMPermanentError, match="401"):
        client.chat([])
    client.close()


def test_chat_raises_transient_on_5xx() -> None:
    client = _make_client(max_retries=0)
    _patch_client(client, [_error_response(503, "unavailable")])
    with pytest.raises(LLMTransientError, match="503"):
        client.chat([])
    client.close()


def test_chat_raises_transient_on_429() -> None:
    client = _make_client(max_retries=0)
    _patch_client(client, [_error_response(429, "rate limit")])
    with pytest.raises(LLMTransientError, match="429"):
        client.chat([])
    client.close()


def test_chat_retries_on_transient_then_succeeds() -> None:
    client = _make_client(max_retries=2)
    # Patch sleep so the test doesn't actually wait.
    with patch("caption_agent.llm.client.time.sleep"):
        _patch_client(client, [
            _error_response(503),
            _error_response(503),
            _ok_response("ok after retries"),
        ])
        result = client.chat([])
    assert result == "ok after retries"
    client.close()


def test_chat_raises_after_max_retries_exhausted() -> None:
    client = _make_client(max_retries=1)
    with patch("caption_agent.llm.client.time.sleep"):
        _patch_client(client, [_error_response(503), _error_response(503)])
        with pytest.raises(LLMTransientError):
            client.chat([])
    client.close()


def test_chat_raises_validation_on_malformed_json_response() -> None:
    bad_body = "this is not json at all"
    response = httpx.Response(200, text=bad_body, headers={"content-type": "application/json"})
    client = _make_client(max_retries=0)
    _patch_client(client, [response])
    with pytest.raises(LLMValidationError):
        client.chat([])
    client.close()


def test_chat_raises_validation_on_missing_choices_key() -> None:
    response = httpx.Response(
        200,
        text=json.dumps({"result": "ok"}),
        headers={"content-type": "application/json"},
    )
    client = _make_client(max_retries=0)
    _patch_client(client, [response])
    with pytest.raises(LLMValidationError):
        client.chat([])
    client.close()


def test_chat_uses_temperature_override() -> None:
    cfg = LLMConfig(base_url="http://localhost/v1", temperature=0.2)
    client = LLMClient(cfg)
    captured: list[dict] = []

    class _CapturingTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured.append(body)
            return _ok_response("x")

    client._http = httpx.Client(transport=_CapturingTransport())
    client.chat([{"role": "user", "content": "hi"}], temperature=0.9)
    assert captured[0]["temperature"] == pytest.approx(0.9)
    client.close()


# ---- Context manager ----

def test_context_manager_closes_client() -> None:
    with _make_client() as client:
        pass
    # httpx.Client should be closed; subsequent requests raise RuntimeError.
    with pytest.raises(RuntimeError):
        client._http.get("http://localhost/")


# ---- _encode_image_as_data_url ----

def test_encode_image_png(tmp_path: Path) -> None:
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG fake")
    url = _encode_image_as_data_url(img)
    assert url.startswith("data:image/png;base64,")
    raw = base64.b64decode(url.split(",", 1)[1])
    assert raw == b"\x89PNG fake"


def test_encode_image_jpeg(tmp_path: Path) -> None:
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8 fake jpeg")
    url = _encode_image_as_data_url(img)
    assert url.startswith("data:image/jpeg;base64,")


def test_encode_image_unsupported_format_raises(tmp_path: Path) -> None:
    img = tmp_path / "model.safetensors"
    img.write_bytes(b"bytes")
    with pytest.raises(LLMPermanentError, match="Unsupported"):
        _encode_image_as_data_url(img)


# ---- _inject_image ----

def test_inject_image_into_string_content() -> None:
    messages = [{"role": "user", "content": "describe this"}]
    result = _inject_image(messages, "data:image/png;base64,abc")
    assert result[0]["role"] == "user"
    content = result[0]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "image_url"
    assert content[1]["type"] == "text"
    assert content[1]["text"] == "describe this"


def test_inject_image_creates_user_message_when_none() -> None:
    messages = [{"role": "system", "content": "you are an analyst"}]
    result = _inject_image(messages, "data:image/png;base64,abc")
    assert result[-1]["role"] == "user"


def test_inject_image_only_injects_into_first_user_message() -> None:
    messages = [
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ]
    result = _inject_image(messages, "data:image/png;base64,abc")
    # Only first user message gets the image.
    assert isinstance(result[0]["content"], list)
    assert isinstance(result[1]["content"], str)


# ---- Thinking-tag stripping ----

def test_chat_strips_think_tags_from_response() -> None:
    """Reasoning models (Qwen3, DeepSeek-R1) emit <think>...</think> inline in content."""
    raw = "<think>\nLet me think about this...\n</think>\n\nmychar01, portrait"
    client = _make_client()
    _patch_client(client, [_ok_response(raw)])
    result = client.chat([{"role": "user", "content": "caption this"}])
    assert result == "mychar01, portrait"
    client.close()


def test_chat_strips_think_tags_leaving_only_content() -> None:
    """Thinking block may precede the actual response with no trailing newline."""
    raw = "<think>reasoning goes here</think>actual caption text"
    client = _make_client()
    _patch_client(client, [_ok_response(raw)])
    result = client.chat([])
    assert result == "actual caption text"
    client.close()


def test_chat_raises_validation_when_only_think_block() -> None:
    """If the entire response is a think block with no real content, raise LLMValidationError."""
    raw = "<think>nothing but thoughts</think>"
    client = _make_client(max_retries=0)
    _patch_client(client, [_ok_response(raw)])
    with pytest.raises(LLMValidationError, match="empty"):
        client.chat([])
    client.close()


def test_chat_no_think_tags_unchanged() -> None:
    """Responses without thinking tags pass through unmodified."""
    raw = "mychar01, looking at camera, studio lighting"
    client = _make_client()
    _patch_client(client, [_ok_response(raw)])
    result = client.chat([])
    assert result == raw
    client.close()


# ---- DEBUG logging tests ----

def test_debug_logs_request_and_response(caplog: pytest.LogCaptureFixture) -> None:
    """At DEBUG level, both the request and the response are logged with previews."""
    client = _make_client()
    _patch_client(client, [_ok_response("a generated caption line")])
    with caplog.at_level("DEBUG", logger="caption_agent.system"):
        client.chat([{"role": "user", "content": "describe this image please"}])
    client.close()

    text = caplog.text
    assert "LLM request →" in text
    assert "describe this image please" in text  # request preview
    assert "LLM response ←" in text
    assert "a generated caption line" in text  # response preview


def test_debug_logging_redacts_image_base64(caplog: pytest.LogCaptureFixture) -> None:
    """Vision image parts are shown as [image] — raw base64 must never be logged."""
    client = _make_client()
    _patch_client(client, [_ok_response("ok")])
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAABBBBCCCC"}},
                {"type": "text", "text": "what is shown here"},
            ],
        }
    ]
    with caplog.at_level("DEBUG", logger="caption_agent.system"):
        client.chat(messages)
    client.close()

    assert "[image]" in caplog.text
    assert "what is shown here" in caplog.text
    assert "AAAABBBBCCCC" not in caplog.text  # base64 redacted


def test_null_content_logs_safe_diagnostic(caplog: pytest.LogCaptureFixture) -> None:
    """content=null failures log response shape without prompt or raw reasoning text."""
    client = _make_client()
    _patch_client(client, [_null_content_response()])
    messages = [{"role": "user", "content": "sensitive prompt text"}]
    with caplog.at_level("WARNING", logger="caption_agent.system"):
        with pytest.raises(LLMPermanentError, match="content is null"):
            client.chat(messages)
    client.close()

    text = caplog.text
    assert "LLM returned content=null" in text
    assert '"finish_reason": "length"' in text
    assert '"payload_has_max_tokens": false' in text
    assert '"reasoning_content_present": true' in text
    assert '"reasoning_content_chars": 38' in text
    assert '"completion_tokens": 512' in text
    assert "sensitive prompt text" not in text
    assert "private reasoning should not be logged" not in text


def test_no_debug_logs_when_level_is_info(caplog: pytest.LogCaptureFixture) -> None:
    """At INFO level the request/response DEBUG lines are not emitted."""
    client = _make_client()
    _patch_client(client, [_ok_response("caption")])
    with caplog.at_level("INFO", logger="caption_agent.system"):
        client.chat([{"role": "user", "content": "hi"}])
    client.close()

    assert "LLM request →" not in caplog.text
    assert "LLM response ←" not in caplog.text


# ---- is_thinking_model ----

@pytest.mark.parametrize("model_id", [
    "qwen/qwen3-235b-a22b",
    "qwen/qwen3.6-35b-a3b",
    "Qwen3-8B",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-distill-qwen-32b",
    "deepseek-r2-zero",
    "provider/model/r1",
    "my-model:thinking",
    "some-model-thinking",
])
def test_is_thinking_model_true(model_id: str) -> None:
    assert is_thinking_model(model_id), f"Expected thinking model: {model_id!r}"


@pytest.mark.parametrize("model_id", [
    "qwen/qwen2.5-72b-instruct",
    "gpt-4o",
    "claude-3-5-sonnet",
    "mistral-7b-instruct",
    "llama-3-70b",
    "deepseek/deepseek-v3",
])
def test_is_thinking_model_false(model_id: str) -> None:
    assert not is_thinking_model(model_id), f"Expected non-thinking model: {model_id!r}"
