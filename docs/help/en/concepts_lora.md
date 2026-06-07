# What is LoRA and why captions matter

Why the quality of training captions directly affects the outcome of fine-tuning.

## For beginners

LoRA is a way to teach an already-trained diffusion model something new without retraining the whole model. You show it a set of images and it memorises what they have in common.

Every image needs a text description — a caption. The caption tells the model what to learn from that image and what to ignore as background noise.

If you don't caption the images at all, or caption them all identically, the model memorises everything: the target subject, the setting, the lighting. When generating later, it will reproduce all of it together — you won't be able to get the same subject in a different setting.

Good captions tell the model: "this part is constant, that part changes every time." The constant part gets tied to the trigger token. The variable part is controlled through your generation prompt.

## For professionals

In LoRA fine-tuning, text captions control feature attribution. An attribute that appears in every image but is not reflected in the captions will "stick" to the trigger token — the model treats it as an intrinsic property of the training subject.

The goal of good captioning is to achieve broad distributional coverage of the controllable variables (pose, clothing, setting, lighting) while excluding stable identity attributes (facial features, eye colour, nose shape) from the captions. The latter the model learns through visual repetition — they do not need a text anchor.

Poorly written captions produce predictable artefacts:

- **Setting binding** — if all images share the same location and the setting is not mentioned in the captions, the model binds it to the trigger token.
- **Clothing binding** — if clothing is described in detail for every image, the model reproduces it even when you don't ask for it.
- **Identity drift** — if captions describe a neutral generic subject rather than the specific one, the model generates something plausible but wrong.

Caption Agent automatically controls these risks through rules specific to your LoRA type.

## Effect on your workflow

Caption Agent forms captions according to the rules defined for your LoRA type. You review the result and adjust where needed — either manually or through the project policy settings.

For LoRA type details, see [LoRA Types](concepts_lora_types.md). For caption policy, see [Caption policy](concepts_policy.md).
