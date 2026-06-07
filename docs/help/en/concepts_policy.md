# Caption policy

How a project controls caption rules through the caption policy.

## For beginners

A caption policy is a set of configurable rules for a specific project. These rules tell the normalizer what to write in captions and tell the rule checker what counts as a violation.

By default, every new project uses the built-in rules — they work for most cases. But if you are training a LoRA for a specific character or style, you can specify the exact traits of that character that must not be named in captions, or specific setting phrases that are too detailed.

The caption policy is set on the project page in the collapsible "Caption policy" panel. Changes take effect on subsequent batches.

## For professionals

The caption policy has six fields:

**Structured fields** (read by the rule checker as machine-readable data):
- `identity_trait_patterns` — regular expressions for identity traits. If any pattern matches in a caption, an IDENTITY_OVERCAPTION warning is generated.
- `setting_overspecific_phrases` — a list of setting phrases. If a phrase appears in a synthetic image caption, a SETTING_OVERSPECIFIC warning is generated.
- `source_ref_required_setting` — required phrase in source reference captions. Default: `gray studio background`.

**Free-text fields** (injected into LLM prompts):
- `coarse_setting_note` — instruction to the normalizer on how to describe the setting. Default enforces the "2–4 words, category of place, no specific details" principle.
- `custom_normalizer_rules` — additional rules for the normalizer, appended to the system prompt.
- `custom_checker_rules` — additional rules for the LLM checker.

A project without an explicit caption policy (NULL in the database) uses the defaults. This means backward compatibility: existing projects behave exactly as before the policy feature was introduced.

## Effect on your workflow

When a batch is created, the project's caption policy is read once and applied to the whole batch. Changing the policy does not reprocess already-processed images — only subsequent batches pick up the change.

For parameter details, see [Caption Policy Parameters](ref_policy_params.md).
