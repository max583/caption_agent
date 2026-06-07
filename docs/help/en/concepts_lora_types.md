# LoRA types

What defines a LoRA type and how it shapes what goes into captions.

## For beginners

Caption Agent supports seven LoRA types. You choose one when creating a project, and it determines what the pipeline considers important when describing images.

| Type | What is being trained |
|---|---|
| **Character** | A specific person's identity: face, pose, clothing, setting |
| **Creature** | A character who is an animal or fantastical creature |
| **Style** | An artistic style: technique, palette, light quality, texture |
| **Clothing** | A specific garment: cut, fabric, colour, construction details |
| **Pose** | A specific pose or movement: limb positions, weight distribution |
| **Object** | A specific physical object: form, material, surface finish |
| **Face** | Portrait identity: expression, camera angle, face lighting |

Training a LoRA on a specific person — choose Character. An artistic style — Style. A specific garment — Clothing.

## For professionals

The LoRA type governs what counts as a training signal versus noise that must be controlled in captions.

**Character and Creature** — training target: identity. Stable traits (eye colour, nose shape, fur colour, exact markings) are excluded from captions — they are learned through visual repetition. Caption slots: framing, view, clothing, pose, setting.

**Style** — training target: visual treatment. Style-describing words (watercolour, photorealistic, cinematic) are required — they are the training signal. Quality boosters (masterpiece, stunning, award-winning) are forbidden.

**Clothing** — training target: a specific garment. Unlike character LoRA, detailed garment description is required: each attribute (cut, fabric, colour, construction details) goes in its own slot. The wearer is fit context only, not the subject of description.

**Pose** — training target: body configuration. Pose description must be detailed: limb positions, movement vector. Expression, lighting, and stable identity traits are excluded.

**Object** — training target: a physical object. Caption slots: object type, material, colour, visible construction details. Camera angle is excluded. Aesthetic judgements (elegant, beautiful) are forbidden.

**Face** — training target: portrait identity. Required: framing, view, expression, face lighting. Clothing and setting only if clearly visible in frame.

> **Important:** every type has dataset binding risks. For example, with Style — if all images show the same subject type, the LoRA will bind the style to that subject. The analytics section warns about these risks automatically.

## Effect on your workflow

The LoRA type cannot be changed after the project is created. It determines the normaliser rules, the set of active checks, and the analyst prompts. When changing subject domains, create a new project.
