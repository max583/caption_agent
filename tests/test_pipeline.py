"""Unit tests for pipeline modules: normalizer response parsing, exporter, llm_pass_checker parsing."""

from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path

from caption_agent.llm.client import LLMValidationError
from caption_agent.logging_setup.llm_io_dumper import LLMIODumper
from caption_agent.pipeline.analyst import _parse_response as parse_analyst
from caption_agent.pipeline.llm_pass_checker import _parse_response as parse_checker
from caption_agent.pipeline.normalizer import _parse_response as parse_normalizer


# ---- analyst._parse_response ----

def test_analyst_parse_valid_json() -> None:
    raw = json.dumps({
        "raw_description": "A young man standing.",
        "pose": "standing",
        "camera_angle": "front",
        "crop": "fullbody",
        "clothing": "wearing a T-shirt and jeans",
        "expression": "neutral",
        "setting": "village yard",
        "other_characters": [],
        "adult_context": False,
        "defects": [],
        "uncertainty_notes": [],
    })
    result = parse_analyst(raw)
    assert result["pose"] == "standing"
    assert result["crop"] == "fullbody"


def test_analyst_parse_json_with_markdown_fence() -> None:
    raw = "```json\n{\"raw_description\": \"desc\", \"pose\": \"sitting\"}\n```"
    result = parse_analyst(raw)
    assert result["pose"] == "sitting"
    assert "raw_description" in result


def test_analyst_parse_json_embedded_in_text() -> None:
    raw = 'Here is the analysis:\n{"raw_description": "x", "pose": "walking"}\nEnd.'
    result = parse_analyst(raw)
    assert result["pose"] == "walking"


def test_analyst_parse_non_json_raises_validation_error() -> None:
    with pytest.raises(LLMValidationError):
        parse_analyst("The image shows a person standing in a field.")


def test_analyst_parse_sets_raw_description_fallback() -> None:
    raw = '{"pose": "running"}'
    result = parse_analyst(raw)
    assert result["raw_description"] == raw  # added as fallback


# ---- normalizer._parse_response ----

def test_normalizer_parse_clean_caption() -> None:
    raw = "mychar01, portrait, front view, wearing a shirt, neutral, daylight, village"
    result = parse_normalizer(raw)
    assert result == raw


def test_normalizer_parse_strips_quotes() -> None:
    raw = '"mychar01, portrait, front view, wearing a shirt, neutral, daylight, village"'
    result = parse_normalizer(raw)
    assert not result.startswith('"')


def test_normalizer_parse_empty_raises() -> None:
    with pytest.raises(LLMValidationError, match="empty"):
        parse_normalizer("")


def test_normalizer_parse_json_response_raises() -> None:
    with pytest.raises(LLMValidationError, match="JSON"):
        parse_normalizer('{"caption": "mychar01 ..."}')


def test_normalizer_parse_too_many_lines_raises() -> None:
    long = "\n".join(["mychar01, line"] * 10)
    with pytest.raises(LLMValidationError, match="lines"):
        parse_normalizer(long)


def test_normalizer_parse_picks_first_nonempty_line() -> None:
    raw = "\nmychar01, portrait, front view, wearing a shirt, neutral, daylight, village\n"
    result = parse_normalizer(raw)
    assert result.startswith("mychar01")


# ---- llm_pass_checker._parse_response ----

def test_checker_parse_empty_array() -> None:
    assert parse_checker("[]") == []


def test_checker_parse_warnings_array() -> None:
    raw = json.dumps([{"code": "TRIGGER_MISSING", "message": "No trigger."}])
    result = parse_checker(raw)
    assert len(result) == 1
    assert result[0]["code"] == "TRIGGER_MISSING"


def test_checker_parse_markdown_fenced_json() -> None:
    raw = "```json\n[]\n```"
    assert parse_checker(raw) == []


def test_checker_parse_explicit_no_issues() -> None:
    assert parse_checker("no issues") == []
    assert parse_checker("No violations") == []


def test_checker_parse_non_json_raises() -> None:
    with pytest.raises(LLMValidationError):
        parse_checker("The caption looks fine.")


def test_checker_parse_filters_non_dict_entries() -> None:
    raw = json.dumps([{"code": "X", "message": "y"}, "bad_entry", 42])
    result = parse_checker(raw)
    # Only the dict entry should survive.
    assert len(result) == 1
    assert result[0]["code"] == "X"


# ---- extract_candidate_prompts (D-102) ----

def test_extract_candidate_prompts_comfyui_multi_node() -> None:
    """Multi-node ComfyUI workflow: positive and negative nodes each produce a candidate."""
    from tools.extract_image_metadata import extract_candidate_prompts

    metadata: dict = {
        "workflow_text_nodes": [
            {"id": 1, "type": "CLIPTextEncode", "title": "Positive Prompt", "texts": ["a man standing in a park"]},
            {"id": 2, "type": "CLIPTextEncode", "title": "Negative Prompt", "texts": ["worst quality, low quality, blurry, deformed, extra fingers, watermark, jpeg, bad anatomy"]},
        ],
        "comfyui_prompt": None,
    }
    result = extract_candidate_prompts(metadata)
    assert len(result) == 2
    positives = [c for c in result if not c["likely_negative"]]
    negatives = [c for c in result if c["likely_negative"]]
    assert len(positives) == 1
    assert len(negatives) == 1
    assert positives[0]["text"] == "a man standing in a park"
    assert "Negative Prompt" in negatives[0]["label"] or negatives[0]["likely_negative"]


def test_extract_candidate_prompts_a1111_parameters() -> None:
    """A1111-style parameters chunk is surfaced as a single candidate."""
    from tools.extract_image_metadata import extract_candidate_prompts

    metadata: dict = {
        "workflow_text_nodes": [],
        "comfyui_prompt": None,
        "png_text": {
            "parameters": {"value": "a portrait, soft lighting\nNegative prompt: ugly, bad anatomy", "chunk_type": "tEXt"},
        },
    }
    result = extract_candidate_prompts(metadata)
    assert len(result) == 1
    assert result[0]["label"] == "parameters"
    assert "portrait" in result[0]["text"]


def test_extract_candidate_prompts_empty_metadata() -> None:
    """Plain photo with no metadata returns empty list."""
    from tools.extract_image_metadata import extract_candidate_prompts

    assert extract_candidate_prompts({}) == []
    assert extract_candidate_prompts({"workflow_text_nodes": [], "comfyui_prompt": None}) == []


def test_extract_candidate_prompts_deduplication() -> None:
    """Identical texts from different nodes appear only once."""
    from tools.extract_image_metadata import extract_candidate_prompts

    same_text = "mychar01, medium shot, front view, wearing a coat"
    metadata: dict = {
        "workflow_text_nodes": [
            {"id": 1, "type": "CLIPTextEncode", "title": "Prompt A", "texts": [same_text]},
            {"id": 2, "type": "CLIPTextEncode", "title": "Prompt B", "texts": [same_text]},
        ],
        "comfyui_prompt": None,
    }
    result = extract_candidate_prompts(metadata)
    assert len(result) == 1


def test_extract_candidate_prompts_negative_detection_threshold() -> None:
    """Text with fewer than 2 negative phrases is NOT tagged likely_negative."""
    from tools.extract_image_metadata import extract_candidate_prompts

    metadata: dict = {
        "workflow_text_nodes": [
            {"id": 1, "type": "CLIPTextEncode", "title": "Text", "texts": ["low quality photography"]},
        ],
        "comfyui_prompt": None,
    }
    result = extract_candidate_prompts(metadata)
    assert len(result) == 1
    assert not result[0]["likely_negative"]


def test_extract_candidate_prompts_analyst_no_prompt_input() -> None:
    """Analyst user message must not contain any generation_prompt text (D-102)."""
    from unittest.mock import MagicMock
    from caption_agent.pipeline.analyst import _build_user_text

    item = MagicMock()
    item.generation_prompt = "some generation prompt that should be ignored"
    text = _build_user_text(item)
    assert "generation prompt" not in text.lower()
    assert "some generation prompt" not in text


# ---- context_reader project-root resolution ----

def test_context_reader_project_root_contains_tools() -> None:
    """_ensure_project_root must point at the dir that actually holds tools/.

    Regression: it previously used parents[3] (scripts/) instead of parents[4]
    (project root), so `from tools.extract_image_metadata import ...` failed and
    was swallowed, leaving generation_prompt empty. pytest's pythonpath masked
    this, so assert the path directly rather than relying on the import working.
    """
    from pathlib import Path

    import caption_agent.pipeline.context_reader as cr

    cr_file = Path(cr.__file__)
    project_root = cr_file.parents[4]
    assert (project_root / "tools" / "extract_image_metadata.py").exists(), (
        f"tools/ not found under resolved project root {project_root}"
    )


# ---- LLMIODumper ----

class TestLLMIODumper:
    def _dumper(self, tmp: Path, enabled: bool = True) -> LLMIODumper:
        return LLMIODumper(dump_dir=tmp / "llm_io", enabled=enabled)

    def test_disabled_writes_nothing(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path, enabled=False)
        d.dump(project_id=1, batch_id=1, item_id=1, step="analyst", request_messages=[], response_text="hi")
        assert not (tmp_path / "llm_io").exists()

    def test_creates_req_and_resp_files(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(
            project_id=2, batch_id=5, item_id=7,
            step="analyst",
            request_messages=[{"role": "user", "content": "describe this"}],
            response_text='{"pose": "standing"}',
            latency_ms=123.4,
        )
        files = list((tmp_path / "llm_io").iterdir())
        names = [f.name for f in files]
        assert any("_req.txt" in n for n in names)
        assert any("_resp.txt" in n for n in names)

    def test_filename_contains_project_batch_step_item(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(project_id=3, batch_id=9, item_id=42, step="normalizer",
               request_messages=[], response_text="ok")
        files = list((tmp_path / "llm_io").iterdir())
        for f in files:
            assert "p3" in f.name
            assert "b9" in f.name
            assert "item42" in f.name
            assert "normalizer" in f.name

    def test_req_file_contains_message_text(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(
            project_id=1, batch_id=1, item_id=1,
            step="checker",
            request_messages=[
                {"role": "system", "content": "You are a checker."},
                {"role": "user", "content": "Check: mychar01, medium shot"},
            ],
            response_text="[]",
        )
        req = next((tmp_path / "llm_io").glob("*_req.txt"))
        text = req.read_text(encoding="utf-8")
        assert "You are a checker." in text
        assert "mychar01" in text
        assert "[system]" in text
        assert "[user]" in text

    def test_resp_file_contains_response_and_latency(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(project_id=1, batch_id=1, item_id=1, step="analyst",
               request_messages=[], response_text="the response text", latency_ms=456.0)
        resp = next((tmp_path / "llm_io").glob("*_resp.txt"))
        text = resp.read_text(encoding="utf-8")
        assert "the response text" in text
        assert "456" in text

    def test_error_written_to_resp_file(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(project_id=1, batch_id=1, item_id=1, step="analyst",
               request_messages=[], response_text=None, error="Connection refused")
        resp = next((tmp_path / "llm_io").glob("*_resp.txt"))
        assert "Connection refused" in resp.read_text(encoding="utf-8")

    def test_image_base64_stripped_in_req_file(self, tmp_path: Path) -> None:
        d = self._dumper(tmp_path)
        d.dump(
            project_id=1, batch_id=1, item_id=1,
            step="analyst",
            request_messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AABBCC=="}},
                    {"type": "text", "text": "describe"},
                ],
            }],
            response_text="ok",
        )
        req = next((tmp_path / "llm_io").glob("*_req.txt"))
        text = req.read_text(encoding="utf-8")
        assert "AABBCC" not in text
        assert "base64 omitted" in text
        assert "describe" in text
