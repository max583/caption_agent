# System Requirements

What you need to install before running Caption Agent.

## For beginners

Caption Agent is a web application that runs on your computer. It needs Python and a few standard tools. You already have a browser.

**What you need:**

- **Python 3.10 or later** — the language the application is written in. Download from [python.org](https://www.python.org/downloads/).
- **pip** — Python's package manager. Included in a standard Python installation.
- **Git** (optional) — if you want to clone the repository. Alternatively, download the zip archive.

The application runs on Windows, macOS, and Linux. There are no special hardware requirements for Caption Agent itself. A GPU is only needed if you are running the LLM locally.

## For professionals

Caption Agent requires Python 3.10+ (uses match statements and SQLAlchemy 2.0 typed mapped columns).

**Dependencies (installed automatically via pip):**

| Package | Minimum version | Purpose |
|---|---|---|
| fastapi | 0.110 | Web framework |
| uvicorn | 0.27 | ASGI server |
| sqlalchemy | 2.0 | ORM |
| alembic | 1.13 | DB migrations |
| pydantic | 2.0 | Validation / schemas |
| httpx | 0.27 | LLM HTTP client |
| Pillow | 10.0 | Image metadata |
| markdown | 3.6 | Help rendering |

**LLM endpoint** — required. Any OpenAI-compatible API: local (LM Studio, Ollama, llama.cpp server) or cloud-hosted. The image analysis step needs a vision-capable model. The normaliser and checker steps only need a text model.

**Database** — SQLite (default, no configuration needed) or PostgreSQL (optional `[postgres]` extra).

## Verification

Check your Python version:

```
python --version
```

This should print `Python 3.10.x` or higher. If it prints `Python 2.x`, install Python 3 separately.

For installation and startup instructions, see [Installation & Launch](launch.md).
