# Settings

Where to configure the language model parameters and system settings.

## For beginners

The Settings page opens via the "Settings" link in the navigation bar. On the left is a section menu; on the right is the content of the selected section.

Sections:
- **LLM** — server address and language model parameters.
- **Retries** — limits on the number of normalisation attempts.
- **Polling** — how often the interface refreshes data.
- **Paths** — file path settings.
- **Logging** — log level and retention.
- **Database** — database information and maintenance tools.
- **Interface** — interface language.

Most parameters are stored in the database and apply immediately without a restart.

> **Tip:** to get started you only need to configure the LLM section — set the address of your model server and choose a model. Everything else can be left at defaults.

## For professionals

### LLM section

The main block sets the global server and model. Additional blocks (Analyst / Normalizer / LLM Checker) allow separate configurations for each pipeline step. Fields left empty in the step blocks inherit from the main block.

LLM profiles let you save and quickly switch between configurations. The active profile is shown in the indicator in the navigation bar.

### Connection test

The "Test connection" button in the LLM section sends a test request to the model and shows the latency in milliseconds. The same 🔌 button is also accessible from the navigation bar.

### Database section

Shows the database file size, record counts, and provides maintenance tools: old journal record cleanup, SQLite vacuum.

For a full parameter reference, see [LLM Settings](ref_llm_settings.md).
