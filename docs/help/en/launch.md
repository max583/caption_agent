# Installation & Launch

How to install Caption Agent and run it for the first time.

## For beginners

### Installation

All commands are run in a terminal (PowerShell on Windows, Terminal on macOS/Linux).

1. Go to the `scripts/caption_agent` folder inside the repository:

```
cd scripts\caption_agent
```

2. Create a Python virtual environment:

```
python -m venv .venv
```

3. Install the application and all dependencies:

```
.venv\Scripts\pip install -e ".[dev]"
```

4. Initialise the database:

```
.venv\Scripts\alembic upgrade head
```

### Running

**On Windows** — the easiest way is to double-click `start.bat` in the `scripts/caption_agent` folder.

Or from the terminal:

```
.venv\Scripts\python -m caption_agent.main
```

Once started, open your browser and go to: **http://127.0.0.1:8765**

To stop the server, press `Ctrl+C` in the terminal.

## For professionals

**Editable install** (`-e`) lets you edit code without reinstalling the package. In dev mode, uvicorn restarts the server automatically when Python files change.

**Dev launch** (hot-reload):

```
start-dev.bat          # Windows
# or:
CAPTION_AGENT_RELOAD=1 CAPTION_AGENT_LOG_LEVEL=DEBUG .venv/bin/python -m caption_agent.main
```

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `CAPTION_AGENT_HOST` | `127.0.0.1` | Server bind address |
| `CAPTION_AGENT_PORT` | `8765` | Server port |
| `CAPTION_AGENT_DB_URL` | `sqlite:///./data/agent.db` | Database URL |
| `CAPTION_AGENT_LOG_LEVEL` | `INFO` | Log level |
| `CAPTION_AGENT_RELOAD` | `0` | `1` to enable hot-reload |
| `CAPTION_AGENT_LLM_API_KEY` | — | API key for all LLM steps |

**Migration note:** schema changes require a manual `alembic upgrade head`. Hot-reload does not handle this automatically.

## After launch

The first page you see is the Projects list — it will be empty. The next step is to create your first project and configure the LLM under Settings.

For an overview of the interface, see [UI Overview](ui_overview.md).
