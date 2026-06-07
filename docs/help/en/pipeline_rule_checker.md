# Step 3: Rule Checker

The third processing step: the rule checker looks for policy violations in the caption text — without calling an LLM.

## For beginners

After the normalizer writes a caption, the rule checker reads it and checks whether it breaks any basic rules. This check is fast — it analyses the text directly, without sending requests to a language model.

What is always checked, regardless of LoRA type:
- Does the caption start with the trigger token?
- Are there any quality or style words ("photorealistic", "cinematic")?
- Are there any negative descriptions like "no wrinkles" or "free of artifacts"?
- Are there multiple characters where there should be one?

Additional checks — such as the presence of a crop type or camera angle — are enabled only for LoRA types where those elements are required.

If a violation is found, a warning with a code is generated and the normalizer gets a chance to fix the caption. If the attempt limit is exhausted, the warning stays on the image record and you make the final call during review.

## For professionals

The rule checker is purely deterministic: regular expressions and logic, no LLM. This lets it run on every normalizer iteration without additional cost.

Warning codes:

| Code | Condition |
|---|---|
| `TRIGGER_MISSING` | Caption does not start with the trigger token |
| `NEGATIVE_WORDING` | A negative constraint was found |
| `MULTI_CHARACTER` | Analyst detected other characters |
| `STYLE_TOKEN` | A style/quality token was found (except type=style) |
| `AGE_PHRASE` | A forbidden age phrase was found (character, face) |
| `ADULT_BRANCH_MISMATCH` | Adult content on the identity branch (character) |
| `IDENTITY_OVERCAPTION` | A stable identity trait is named explicitly (character, face, creature) |
| `NUDE_ON_CROPPED_PORTRAIT` | "nude"/"naked" on a cropped portrait (character, face) |
| `SOURCE_REF_PATTERN_VIOLATION` | Source reference caption format violation (character) |
| `FRAMING_INVALID` | No canonical crop type token (character, face, clothing, creature, pose) |
| `VIEW_INVALID` | No canonical camera angle token (character, face, clothing, creature, pose) |
| `SLOT_MISSING` | Required slots are missing (character, clothing, creature, object) |
| `SETTING_OVERSPECIFIC` | Setting is described with too much specificity (character, clothing, creature, object) |

The first three codes (`TRIGGER_MISSING`, `NEGATIVE_WORDING`, `MULTI_CHARACTER`) apply to all LoRA types. The remaining codes are gated by LoRA type: the types for which each code is active appear in parentheses.

> **For type=style:** only TRIGGER_MISSING, NEGATIVE_WORDING, and MULTI_CHARACTER are checked — almost all other codes are not applicable to captions that describe visual technique.

The patterns for `IDENTITY_OVERCAPTION` and `SETTING_OVERSPECIFIC` come from the project's caption policy. If no policy is configured, default patterns are applied.

## Effect on your workflow

Rule checker warnings are passed back to the normalizer as feedback. The normalizer sees the code and message and tries to write a corrected caption. This loop repeats until the attempt limit is reached.

After passing the rule checker, the caption moves to the LLM checker.

For LLM checker details, see [Step 4: LLM Checker](pipeline_llm_checker.md).
