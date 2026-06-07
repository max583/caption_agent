# How to add custom rules?

**The normalizer or LLM checker systematically misses something specific to my project.**

## Direct answer

The caption policy lets you add extra instructions directly into the prompts — without changing any code.

## Step-by-step solution

### If you need a new instruction for the normalizer

1. Open the project page.
2. Expand the "Caption policy" panel → click "Edit".
3. In the "Custom normalizer rules" field, write your instruction in English. For example:
   - `Always describe the character's hair as "dark brown hair" — never write "black hair".`
   - `If the character is wearing a hat, always specify its color.`
4. Save.

The instruction will be appended to the normalizer's system prompt on the next processing run.

### If you need the LLM checker to catch a specific violation

1. In the same "Caption policy" panel, fill in the "Custom checker rules" field.
2. Describe what counts as a violation and why. For example:
   - `Flag any caption that mentions "blue eyes" — the character's eyes are grey.`
3. Save.

### If you need to forbid specific phrases via the rule checker

Use the structured fields for this:
- **Identity trait patterns** — add a regular expression for the forbidden phrase.
- **Setting over-specificity phrases** — add a specific background detail phrase.

These fields are read by the rule checker without LLM — fast and at no additional cost.

## Important note

Changes to the caption policy apply only to subsequent batches. Already-processed images are not automatically reprocessed. To regenerate the caption for a specific image — click Regenerate in review.

## References

For policy field details, see [Caption Policy Parameters](ref_policy_params.md).
For the policy concept, see [Caption Policy](concepts_policy.md).
