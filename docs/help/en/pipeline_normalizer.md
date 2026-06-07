# Step 2: Normalizer

The second processing step: the normalizer turns the analyst's description into a finished training caption.

## For beginners

The analyst described the image in structured form — now the normalizer takes that description and formats it into a strict, single-line caption.

What the normalizer does:
- Starts every caption with your project's trigger token.
- Chooses a caption format that matches the project's LoRA type: for a character project this means pose, clothing, and setting; for a style project — rendering technique and colour palette; for a clothing project — cut, material, and construction details.
- Follows caption policy rules: does not add quality words, does not write a default age phrase.
- If a previous attempt received warnings from the rule checker, the normalizer sees them and corrects the caption on its next attempt.

The output is a single line of text. That line is what goes into the training dataset.

## For professionals

The normalizer makes an LLM call with a system prompt that has been filled in with: the project's trigger token, the LoRA type, and instructions from the project's caption policy (if configured). The inputs are the analyst output and batch context (source_type, branch).

Caption structure depends on the LoRA type. Each type has a separate normalizer prompt with its own slot template. The trigger token is required for all types and always comes first; the remaining slots differ. The full list of templates is in [Caption Formats by LoRA Type](pipeline_normalizer_formats.md).

If the previous normalizer iteration received warnings from the rule checker, they are passed back to the normalizer as feedback. The normalizer makes another attempt — fixing the flagged violations without introducing new ones.

Caption policy enforced at this step:

- no style tokens (photorealistic, cinematic, etc.) — all types
- setting described as a category of place, not specific details — character, face, pose, creature
- age not mentioned by default — character, face
- nudity on a cropped portrait described as "bare shoulders visible" — character, face
- source reference captions use a fixed format — character

> **For clothing LoRA:** detailed description of every garment attribute is the training goal, not a violation. The wearer is mentioned only as fit context.

The normalizer must return exactly one line of text. An empty response, a JSON response, or a response with three or more lines is treated as invalid and a retry is requested.

## Effect on your workflow

The normalizer result is the `normalized_caption` field on the image record. After normalisation the caption immediately goes through the rule checker. If the rule checker returns warnings, the normalizer is run again (up to the attempt limit configured in settings).

For attempt limit details, see [Project Parameters](ref_project_params.md). For rule checker details, see [Rule Checker](pipeline_rule_checker.md).
