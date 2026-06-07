# Dataset Analysis

Analytics assesses dataset balance and gives concrete advice on fixing the composition — so you know what images are missing before the next generation run.

## For beginners

The project page has a collapsible "Dataset analysis" panel. Click it — Caption Agent counts the distribution of images across key characteristics, and the language model produces up to five recommendations.

The set of characteristics analysed depends on the LoRA type. For example, for a character LoRA:
- **Crop** — how many images are full body, waist-up, portrait.
- **Camera angle** — front, side, back, other.
- **Pose** — distribution across pose descriptions.
- **Expression** — facial expression variety.
- **Clothing state** — clothed, bare shoulders, underwear-only, nude.

For a style LoRA, pose and clothing are replaced by `style descriptor`, `medium/technique`, and `lighting mood`. For a clothing LoRA — garment type, cut/silhouette, material.

Regardless of type, the following are always shown:
- **Source type** — synthetic vs reference.
- **Warnings** — which codes appear most frequently.

You receive concrete suggestions: "add full-body images", "too many front-facing angles", "not enough lighting variety".

## For professionals

Analysis runs in two passes:

**First pass (no LLM)** — statistics over accepted and awaiting-review images for the whole project. Characteristics are read directly from the analyst's structured output. The set of fields depends on the LoRA type: for character — crop, camera_angle, pose, expression, clothing; for style — style_descriptor, medium_technique, lighting_mood; and so on. Clothing state for character is classified from free text into fixed buckets.

**Second pass (LLM)** — the language model receives the aggregate statistics and up to 20 caption examples. From these it generates up to five recommendations with `priority`, `area`, `message`, and `suggestion` fields. The prompt is parameterised by LoRA type: recommendations for a character LoRA differ from those for a style LoRA.

Analysis only includes images in APPROVED and AWAITING_REVIEW states — images in ERROR or DROPPED are excluded.

Recommendations are diagnostics, not blockers. They do not affect the ability to export the dataset.

## Effect on your workflow

Run analysis before the next image generation iteration. The recommendations tell you which image types are underrepresented so training can be well-balanced.

For how to read the recommendations, see [Reading Recommendations](analytics_reading.md).
