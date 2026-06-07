# Trigger token

What a trigger token is and why it appears first in every caption.

## For beginners

A trigger token is a unique word you assign to your LoRA. When you later include it in a generation prompt, the model understands: "activate what you were trained on."

For example, if your trigger token is `mychar01`, every training caption starts with it:

```
mychar01, waist portrait, front view, blue denim jacket, city street
```

The model sees thousands of images, each beginning with `mychar01`. It starts associating that word with everything that is consistently present across the images — that is, the training subject itself.

> **Important:** the trigger token must be unique — it should not be a word that already exists in the model's vocabulary. Ordinary words already carry meaning and will interfere with training. Use invented words or letter-digit combinations: `mychar01`, `xstyle22`, `lora_fox`.

## For professionals

The trigger token is a text anchor that activates the LoRA adapter weights. Having the token in every training caption ensures that all visual features common to the dataset are attributed to this token through the text conditioning mechanism.

The token must be out-of-distribution relative to the base model. Vocabulary words have established embeddings; the tokeniser will split them into familiar sub-tokens and dilute the signal.

The optimal choice is a short, meaningless word. Underscores, digits, and unusual letter combinations reduce the chance of collision with existing tokens. Spaces are not allowed — the token must be a single token.

Caption Agent automatically prepends the trigger token to every caption. It can be changed in the project settings — but only before training begins. Changing the token after training renders the LoRA non-functional for generation.

## Effect on your workflow

The rule checker verifies that the trigger token is present in every caption. If it is absent, the caption fails the check and the normaliser rewrites it.

The project's trigger token is set in the project settings. For details, see [Project Parameters](ref_project_params.md).
