# What's the difference between rule checker and LLM checker?

**The batch workspace shows warnings from two different sources. What is the difference?**

## Direct answer

These are two different pipeline steps that check different things.

**Rule checker** — deterministic, no LLM. Checks the caption text against regular expressions and rules: is the trigger token present, are there any forbidden words, does the structure match the format. Fast and always returns the same result for the same text.

**LLM checker** — semantic, via LLM. Checks whether the caption matches the image, whether there are any hidden policy violations, whether there are logical contradictions. It looks at the caption and the analyst data together.

## What each checks

| Rule checker | LLM checker |
|---|---|
| Trigger token at start | Caption matches the image |
| Style tokens | Implicit age phrases |
| Forbidden words and phrases | Contradictions between fields |
| Crop and angle tokens present | Custom rule violations |
| Caption structural completeness | Semantic inconsistencies |

## Why both matter

The rule checker is a safety net for mechanical violations: it catches format errors quickly and cheaply. The LLM checker is the last barrier before review: it catches what regular expressions cannot.

## References

For rule checker details, see [Rule Checker](pipeline_rule_checker.md).
For LLM checker details, see [LLM Checker](pipeline_llm_checker.md).
