# Caption Agent

A local web application for generating, reviewing, and managing training captions for LoRA fine-tuning. Connects to any OpenAI-compatible LLM endpoint.

## Overview

Caption Agent automates the most labour-intensive part of building a LoRA dataset: turning a folder of images into consistent, policy-compliant training captions. A two-step LLM pipeline — visual analysis followed by text normalisation — produces structured captions while a rule-based checker and a second LLM pass catch violations before they reach the training set.

The app runs entirely on your local machine. No cloud services required beyond the LLM endpoint of your choice.

## Screenshots

**Project page — batch in awaiting review**

![Project page](images/batch_form.png)

**Batch workspace — items list with states and warnings**

![Batch workspace](images/items_form.png)

**Settings — LLM configuration with per-step overrides**

![Settings](images/settings_form.png)

## Features

### Caption pipeline

Each image passes through four automatic steps before reaching manual review:

1. **Analyst** — a vision LLM describes the image in structured JSON. The schema adapts to the LoRA type: a character project gets pose, crop, clothing, expression; a style project gets style descriptor, medium, lighting mood; a clothing project gets garment type, cut, material, and so on.
2. **Normaliser** — a text LLM converts the analyst's JSON into a single training caption string following the project's caption policy (trigger token, slot order, forbidden tokens, etc.).
3. **Rule checker** — deterministic, no LLM. Validates trigger token presence, canonical framing/view vocabulary, prohibited phrases, and policy-level constraints. Active checks are gated per LoRA type.
4. **LLM checker** — a second LLM pass catches semantic violations the rule checker cannot: implicit age phrases, clothing description inconsistent with crop, subject described too specifically in a style caption, and violations of custom checker rules.

If either checker returns warnings the normaliser reruns with feedback, up to a configurable retry limit.

### Seven LoRA types

| Type | Training target | Key caption slots |
|---|---|---|
| **character** | Person identity | crop · camera angle · pose · expression · clothing state |
| **face** | Portrait identity | crop · camera angle · expression · skin tone · facial structure |
| **pose** | Body pose / action | pose action · body silhouette · crop · camera angle |
| **style** | Visual style | style descriptor · medium/technique · lighting mood |
| **clothing** | Garment | garment type · cut/silhouette · material · colour · how worn |
| **creature** | Non-human character | creature type · pose · body covering · camera angle |
| **object** | Physical object | object type · material · form/shape · surface finish |

### Caption policy

Each project carries a caption policy — a set of rules layered on top of the built-in checks:

- Custom forbidden phrases and required phrases
- Custom LLM checker rules (free-text instructions passed directly to the checker prompt)
- Per-project trigger token and target branch (identity / adult)

### Dataset analytics

The project page includes an analytics panel that runs on demand:

- **Statistics pass** — distribution of analyst output fields across all approved and awaiting-review images, broken down by LoRA type and by batch.
- **LLM recommendations** — up to five prioritised suggestions based on the distributions and a caption sample. Prompts are parameterised by LoRA type.

### In-app help

31 help pages in Russian and English, served from the `/help` section. Covers all pipeline steps, batch/image lifecycle state machines (with Mermaid diagrams), all seven LoRA type caption formats, analytics, settings, and FAQ.

### Other

- **Batch queue** — single-lane FIFO; one batch processed at a time; crash recovery on restart.
- **Scheduled batches** — start a batch automatically at a given time.
- **LLM profiles** — save and switch named LLM configurations without re-entering credentials.
- **PostgreSQL support** — SQLite by default; swap in Postgres with the `[postgres]` extra.
- **Bilingual UI** — Russian and English, switchable per session.

## Tech stack

| Layer | Choice |
|---|---|
| Web framework | FastAPI |
| Templates | Jinja2 (server-rendered) |
| Frontend | HTMX + Alpine.js + Tailwind CSS |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Database | SQLite (default) / PostgreSQL |
| LLM client | OpenAI-compatible HTTP |

No JavaScript build step. No SPA framework. The UI is deliberately minimal — this is a local tool, not a SaaS product.

## Requirements

- Python 3.10 or newer
- Any OpenAI-compatible LLM server (LM Studio, Ollama, vLLM, Jan, OpenRouter, …)
- A vision-capable model for the analyst step
- A text model for the normaliser and checker steps (can be the same model)

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\pip install .
.venv\Scripts\alembic upgrade head

# Linux / macOS
.venv/bin/pip install .
.venv/bin/alembic upgrade head
```

For PostgreSQL support add the extra:

```bash
pip install ".[postgres]"
```

<details>
<summary>Developer install</summary>

```bash
pip install -e ".[dev]"   # editable mode + pytest + ruff
```

</details>

## Running

```bash
# Windows — convenience launcher
start.bat

# or directly
.venv\Scripts\caption-agent-server

# with hot-reload (development)
start-dev.bat
```

Server starts at `http://127.0.0.1:8765` by default.

Override host/port via environment variables:

```
CAPTION_AGENT_HOST=0.0.0.0
CAPTION_AGENT_PORT=8080
```

## Configuration

All runtime settings are stored in the database and editable through the Settings page. The only configuration needed before first use is the LLM endpoint — set the Base URL and Model ID in **Settings → LLM**.

To use a different database:

```
CAPTION_AGENT_DB_URL=postgresql+psycopg2://user:pass@localhost/caption_agent
```

## Running tests

```bash
.venv\Scripts\python -m pytest tests\ -q
```

The smoke tests (end-to-end against a real LLM) are skipped by default. Enable them by setting `CAPTION_AGENT_SMOKE_LLM_URL`.

## Project structure

```
caption_agent/          Python package
├── api/                FastAPI routers
├── pipeline/           Analyst, normaliser, rule checker, LLM checker, exporter
├── analysis/           Dataset statistics and LLM recommendations
├── orchestration/      Batch queue, scheduler, crash recovery
├── models/             SQLAlchemy ORM
├── config/             Settings management and caption policy
├── llm/                OpenAI-compatible client with retry
├── services/           Help page renderer
└── prompts/            LLM prompt templates (one file per step × LoRA type)
alembic/                Database migrations
templates/              Jinja2 templates
static/                 CSS
docs/help/              In-app help pages (ru + en)
tests/                  pytest test suite
```
