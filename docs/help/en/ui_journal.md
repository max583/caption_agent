# Journal

Where to view processing events and diagnose problems.

## For beginners

The Journal page opens via the "Journal" link in the navigation bar. It shows all events that occurred during batch processing.

Each record contains:
- **Time** — when the event occurred.
- **Level** — INFO, WARNING, ERROR.
- **Event type** — a short technical name.
- **Message** — what happened.

Clicking a row expands it and shows additional details: project ID, batch ID, image item ID.

Use the filters at the top of the page to find the events you need: by level, project, date range, and message text.

> **Tip:** if a batch is stuck or an image is frozen in ERROR state — start with the Journal. Filter by ERROR level for the relevant project.

## For professionals

The journal contains business events: batch start and completion, image state transitions, LLM call errors. System operational logs are written to a file (path configured in settings) and are not displayed in the journal.

The "Delete filtered" button removes all records matching the current filters. This is useful for clearing stale logs. The retention period is configured under Settings → Logging.

The `#batchN` links in journal rows are clickable and lead directly to the batch workspace.

## Effect on your workflow

The journal is the primary diagnostic tool. When an LLM call fails, the record contains the error code and server message. When the normalisation attempt limit is exhausted, the record contains the final warnings that caused the caption to fail the check.

For retention settings, see [LLM Settings](ref_llm_settings.md).
