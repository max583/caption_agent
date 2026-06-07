# What is Caption Agent

A local tool for automatically generating captions for images used in LoRA training.

## For beginners

When training a LoRA in Stable Diffusion or FLUX, every training image needs a text description — a caption. The more accurate and consistent these descriptions are, the better the LoRA will learn what you are teaching it.

Caption Agent does this work for you. You point it at a folder of images, configure a few project settings, and the tool automatically describes each image, checks the description against your rules, and presents it for your approval.

Caption Agent runs locally on your machine. No images are sent anywhere — except to the LLM you configure yourself.

## For professionals

Caption Agent is a pipeline for generating training captions with deterministic quality control. The core goal: achieve distributional coverage of the target attributes while minimising binding of irrelevant features.

Each image passes through a four-step chain: structured analysis via a vision LLM, normalisation into the final caption string, deterministic rule checking (no LLM), and semantic checking via LLM. The result goes to manual review before export.

The tool supports seven LoRA types with different captioning logic: character, creature, style, clothing, pose, object, and face. Each type changes what counts as a target attribute versus noise.

A caption policy — a per-project configurable rule set — lets you define identity patterns, setting phrases, normaliser rules, and checker rules without editing prompts.

## Effect on your workflow

Caption Agent does not touch your source files. It reads images, stores captions in a local database, and presents them for review. Only after your approval are captions exported as `.txt` sidecar files next to the images — in the format accepted by most LoRA trainers.

For details on the pipeline steps, see [Architecture & Components](pipeline_overview.md).
