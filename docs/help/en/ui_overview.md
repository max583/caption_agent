# UI Overview

The overall structure of the Caption Agent interface.

## For beginners

Caption Agent opens in a browser at `http://127.0.0.1:8765`. The interface is dark-themed. A navigation bar runs along the top and is present on every page.

### Navigation bar

On the left — the "Caption Agent" logo, which is also a link to the home page.

On the right — a row of elements:

- **LLM indicator** — shows the active profile name and model ID. Coloured dot: green = connection verified, red = error, grey = status unknown. The 🔌 button next to it runs a quick connection test with the language model.
- **Projects** — go to the project list.
- **Settings** — LLM and system settings.
- **Journal** — event log for processing.
- **?** — the help section (this page).
- **Language switch** — switches the interface between Russian and English.

### Main content area

Below the navigation bar is the main workspace. The content depends on the current page.

Toast notifications appear in the bottom-right corner — they report successful actions or errors.

## For professionals

The interface is built on HTMX + Alpine.js. Most updates are driven by HTMX: only the changed part of the page is replaced, without a full reload. Navigation state is determined from the full HTML response.

Auto-refresh intervals are configured under Settings → Polling. The project page refreshes every 15 seconds; an active batch workspace refreshes every 7 seconds.

The interface language is stored in the database and applied to all pages. Switching is done via the `RU / EN` button in the navbar.

## Effect on your workflow

Most actions are performed directly on the relevant page — without extra dialogs or modals. Confirmation buttons appear only for destructive actions (deleting a project, a batch, or clearing the log).
