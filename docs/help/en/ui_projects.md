# Projects page

The main entry point to the application: the project list and the project workspace.

## For beginners

When you open Caption Agent you land on the Projects page. It shows a list of all your projects. One project is one LoRA.

### Creating a project

Click the "+ Create project" button. Fill in the form:

- **Name** — any label, for example `My Character v001`.
- **Description** — optional, for your own notes.
- **LoRA type** — what you are training: character, style, clothing, etc.
- **Base model** — the model family, for example `flux` or `sdxl`.

After creating the project you land on the project page.

### The project page

Three main blocks:

1. **Project card** — name, trigger token, LoRA type, base model. The Edit button lets you change these settings.

2. **Dataset analysis** — a collapsible panel with recommendations about batch composition. Loads on click.

3. **Caption policy** — a collapsible panel with caption rule settings for this project.

4. **Batch list** — all batches in the project with their current state. The "Create batch" button opens the creation form.

### Creating a batch

In the creation form:

- **Name** — for example `iter1_portraits`.
- **Image folder** — path to a folder on your machine. The Browse button opens a folder picker.

After creation the batch appears in the list and is immediately placed in the processing queue.

## For professionals

A project is the top level of the hierarchy: one project = one trigger token = one LoRA. All batches in the project inherit the project's trigger token and LoRA type.

Deleting a project cascades to all batches and image records in the database. Source files and already-exported `.txt` sidecar files are not affected.

Dataset analysis is aggregated statistics across all completed batches in the project. Warnings are generated based on the attribute distribution in accepted captions.

## Effect on your workflow

The trigger token and LoRA type cannot be changed if the project already has processed batches with accepted captions — this would create data inconsistency. Create a new project if you need to change these settings.

For the batch workspace, see [Batch Workspace](ui_batch.md).
