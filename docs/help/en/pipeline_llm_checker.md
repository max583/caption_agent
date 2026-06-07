# Step 4: LLM Checker

The fourth processing step: the LLM checker validates the caption semantically — the things that regular expressions cannot catch.

## For beginners

The rule checker can find obvious text-level violations. But some problems are invisible to it: for example, a caption that follows all the rules perfectly but describes something completely different from what is in the image.

The LLM checker sends the caption and the analyst's description to a language model. The model looks at several things at once:
- Does the caption match what the analyst described in the image?
- Are there any hidden policy violations that a regular expression would miss?
- Are there any contradictions between the descriptions?

The result is a list of warnings or an empty list (all is well). Warnings are added to the image record and are visible during review.

> **Note:** the LLM checker is the last automatic step. After it the image waits for your decision during review. Its warnings do not trigger a re-normalisation automatically.

## For professionals

The LLM checker makes an LLM call with a system prompt selected for the project's LoRA type and caption policy. Each type has its own checker prompt with its own set of rules. The inputs are the normalised caption, source_type, branch, and the relevant analyst output fields (those present in the record for this LoRA type).

The model response is parsed as a JSON array of `{code, message}` objects. An empty array means no warnings.

LLM checker warnings are tagged `source: llm_pass_checker` and appended to the image's existing warning list. During review you see rule checker and LLM checker warnings together in one place.

Typical problems the LLM checker catches that the rule checker misses:

- **character, face:** implicit age phrases ("student", "child"), clothing description inconsistent with crop, contradiction between the analyst's adult_context field and the caption
- **clothing:** wearer description (face, name, age) instead of garment description
- **style:** subject described too specifically (a real location or recognisable person named)
- **all types:** violations of custom checker rules from the caption policy's custom_checker_rules

## Effect on your workflow

After the LLM checker, the image moves to AWAITING_REVIEW state. Warnings do not block — they are visible during review and the final decision is yours.

For review details, see [Batch Workspace](ui_batch.md).
