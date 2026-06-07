# Step 1: Analyst

The first processing step: the analyst looks at the image and describes what it shows.

## For beginners

When an image enters the queue, the analyst is first to act. It sends the image to a vision language model and receives back a structured description.

What the analyst describes depends on the project's LoRA type. For a character project it records pose, clothing, facial expression, and setting. For a style project — rendering technique, colour palette, and texture. For a clothing project — the garment's cut, material, and construction details.

The result is saved and passed to the next step — the normalizer. The analyst does not write a caption itself — it only describes.

For the full field list for each type, see [Analyst Schemas by LoRA Type](pipeline_analyst_schemas.md).

## For professionals

The analyst makes a VLM call with a system prompt selected for the project's LoRA type. Each type has a separate prompt with its own JSON schema. The model response is parsed as JSON. If parsing fails, the processor records an error and retries with a raised temperature.

The analyst works from pixels only. The generation prompt used to create the image is not passed to the analyst.

Despite different fields across types, all schemas share three common fields:

| Field | Content |
|---|---|
| `raw_description` | Free-text image description in 1–3 sentences |
| `defects` | Generation artefacts, anatomy errors |
| `uncertainty_notes` | What the analyst could not determine unambiguously |

Some fields present in most types are used by the rule checker: other characters produce a MULTI_CHARACTER warning, adult content on the identity branch produces ADULT_BRANCH_MISMATCH.

## Effect on your workflow

The analyst output determines everything downstream. The normalizer builds the caption from this description.

If the analyst produced a poor description, the final caption will likely be wrong too. In review, choosing Regenerate rather than Accept is the right call in these cases.

For image state details, see [Image Lifecycle](pipeline_image_lifecycle.md).
