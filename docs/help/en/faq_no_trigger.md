# Why doesn't the caption start with the trigger token?

**The caption should start with the project's trigger token, but it doesn't.**

## Direct answer

The normalizer forgot to put the trigger token at the start of the caption. The rule checker noticed (TRIGGER_MISSING warning) and asked for a retry, but either all attempts were exhausted or the error was repeated on each attempt.

## What to do

1. Open the batch workspace and go to the Review tab.
2. Find the image with the TRIGGER_MISSING warning.
3. Click Regenerate — the normalizer will run again.
4. If the error persists after regeneration — check that the trigger token is set correctly in the project settings.

## Why this might happen systematically

If TRIGGER_MISSING appears on many images, the cause is likely one of two things:

- **The model is too "creative"**: lower the temperature slightly or switch models. Some models follow strict format requirements poorly.
- **The trigger token looks like a common word**: for example `person` or `man`. Change it to a meaningless string.

## References

For trigger token details, see [Trigger Token](concepts_trigger.md).
For the TRIGGER_MISSING code, see [Rule Checker](pipeline_rule_checker.md).
