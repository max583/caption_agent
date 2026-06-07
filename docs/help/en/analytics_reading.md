# Reading Recommendations

What dataset composition recommendations mean and how to act on them.

## For beginners

After clicking the "Dataset analysis" panel you see a list of recommendations. Each one looks something like this:

> **Add full-body images**
> The dataset is 80% portrait crops and only 5% full-body images. This may cause the model to not reproduce the character's body correctly below the shoulders.

Recommendations come at three priority levels:
- **High** — a serious imbalance that will likely affect training quality.
- **Medium** — an undesirable skew worth correcting.
- **Low** — a useful improvement but not critical.

You do not need to address all recommendations at once. Start with the high-priority ones.

## For professionals

Recommendations are built from distributions across four axes: crop, camera angle, clothing state, and pose. The language model also reads a sample of 20 captions — this lets it catch semantic skews not visible in counters.

### Common issues and their interpretation

**Crop.** A dataset dominated by portrait / head-and-shoulders crops may train the model to reproduce the face well but the body poorly. For a character LoRA you need balance: portraits, waist portraits, and fullbody shots.

**Camera angle.** Predominantly front-view shots will train the model to "snap" the character to front facing on any request. Add 3/4 angle, profile, and back-view shots.

**Clothing state.** If all images show the same clothing type, the model risks binding that clothing to the trigger token. Variety is essential.

**Pose.** A dataset of only "standing straight" static poses will limit the model's range. Add dynamic poses.

**Warnings.** A high count of STYLE_TOKEN or IDENTITY_OVERCAPTION warnings indicates a systemic problem with the prompt or caption policy — worth investigating before adding more images.

### When recommendations may not apply

- For a style LoRA, crop recommendations are less relevant — what matters there is diversity of styles, not frame structure.
- If the dataset is intentionally uniform (for example, only reference shots from one angle) — a diversity recommendation may be deliberately ignored.

For analysis details, see [Dataset Analysis](analytics_overview.md).
