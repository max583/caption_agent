# LLM Settings

Parameters for the language models used in the pipeline. Located under Settings → LLM.

## For beginners

Caption Agent uses language models at three pipeline steps: analyst, normalizer, and LLM checker. Each step can use a separate model or all can share one.

In the LLM section you configure:
- The address and parameters of the main model server.
- Optionally — separate settings for each step.

Caption Agent works with any OpenAI-compatible server: LM Studio, Ollama, vLLM, Jan, and others.

## For professionals

### Main LLM block

| Parameter | Default | Description |
|---|---|---|
| `base_url` | `http://localhost:1234/v1` | Base URL of the OpenAI-compatible server |
| `api_key` | empty | API key. Can be set via the `CAPTION_AGENT_LLM_API_KEY` environment variable |
| `model_id` | `qwen3.6-35b-a3b` | Model identifier, passed as `model` in requests |
| `context_length` | `0` | Maximum context length (0 = auto) |
| `max_tokens` | `0` | Maximum response tokens (0 = no limit; use 0 for thinking models) |
| `temperature` | `0.2` | Generation temperature |
| `request_timeout` | `600` | Request timeout in seconds |
| `max_retries` | `4` | Number of retries on network or parsing errors |

### Per-step overrides

Each step (analyst / normalizer / LLM checker) has a separate override block. Fields left empty inherit from the main block. Filled fields override the main block for that step only.

Environment variables for per-step API keys:
- `CAPTION_AGENT_ANALYST_LLM_API_KEY`
- `CAPTION_AGENT_NORMALIZER_LLM_API_KEY`
- `CAPTION_AGENT_CHECKER_LLM_API_KEY`

### LLM profiles

LLM settings can be saved as named profiles. One profile can be marked as "active" — it is used by the pipeline. Profiles are useful for switching between different servers or models without re-filling fields manually.

### Retry section

| Parameter | Default | Description |
|---|---|---|
| `normalizer_max_self_retries` | `3` | Maximum normalizer iterations when rule checker returns warnings |
| `consecutive_failure_threshold` | `10` | Number of consecutive batch errors before the pipeline halts |

### Polling intervals section

How often the UI refreshes data (in seconds).

| Parameter | Default |
|---|---|
| Projects list | `30` |
| Project page | `15` |
| Batch in processing | `7` |
| Batch in idle state | `30` |

### Logging section

| Parameter | Default | Description |
|---|---|---|
| `business_log_retention_days` | `30` | Business log retention (days) |
| `debug_dump_llm_io` | off | Write raw LLM requests/responses to files (for debugging) |
| `log_level` | `INFO` | System log level: DEBUG / INFO / WARNING / ERROR |
