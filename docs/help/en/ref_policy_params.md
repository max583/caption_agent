# Caption Policy Parameters

Description of each caption policy field.

---

### Identity trait patterns

**For beginners:** a list of descriptions that must not appear in captions. If you are training a LoRA for a specific character with grey eyes — add "gray eyes" to this list. A caption should not name features that are identical across all images, or the model will treat them as required rather than visual.

**For professionals:** each entry is a Python regular expression. The rule checker compiles them into a combined regex and matches the caption. A match produces an IDENTITY_OVERCAPTION warning. Patterns do not affect the normalizer directly — only the check.

**Examples:**
- `gray eyes` — grey eyes
- `ordinary body build` — ordinary physique
- `consistent dark hair` — consistently dark hair

**Format:** list of Python regex strings. Default: 10 patterns describing Denis character traits.

---

### Setting over-specificity phrases

**For beginners:** if the same specific background detail appears in many captions, the model binds it to the trigger token. Add such phrases to this list so the rule checker warns when they appear.

**For professionals:** substring matching (no regex). A match in a synthetic image caption produces a SETTING_OVERSPECIFIC warning. Applied only to synthetic images, not references.

**Examples:**
- `wooden building`
- `log cabin`
- `blurred green foliage`

**Format:** list of strings. Default: 12 phrases typical for the Denis dataset.

---

### Required setting for source references

**For beginners:** what must appear in every caption for a real reference image. Usually a studio background description.

**For professionals:** the rule checker checks for this substring in captions with `source_type=reference`. If absent → SOURCE_REF_PATTERN_VIOLATION warning.

**Format:** string. Default: `gray studio background`.

---

### Coarse setting note for normalizer

**For beginners:** a hint for the language model on how to describe the setting. The more explicit the constraint, the easier it is for the model to understand that "outdoor setting" is correct and "in front of a specific crumbling concrete wall" is not.

**For professionals:** injected into the normalizer's system prompt via the `{coarse_setting_note}` placeholder. Write in imperative style, 1–4 sentences.

**Format:** free-text string. Default: enforces the "2–4 words, category of place" principle.

---

### Custom normalizer rules

**For beginners:** if the normalizer keeps making the same mistake — describe here what should be different. This text is appended to the end of the normalizer's system prompt.

**For professionals:** appended to the system prompt after the main rules. No standard format — write as an instruction in English. For maximum effect, use concrete examples or an explicit prohibition.

**Format:** string or empty. Default: empty.

---

### Custom checker rules

**For beginners:** additional criteria for the LLM checker. If you want it to warn about something specific — describe it here.

**For professionals:** injected into the LLM checker's system prompt. Independent from the normalizer — you can set checker-only rules without touching the normalizer prompt.

**Format:** string or empty. Default: empty.
