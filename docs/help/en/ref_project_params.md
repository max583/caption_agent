# Project Parameters

Description of all fields that are set when creating and editing a project.

---

### Name

**For beginners:** any label — the name of your LoRA. For example `Denis v001` or `MyStyle`.

**For professionals:** a string up to 255 characters. Must be unique across all projects in the database. Used as a label in the project list and in URLs.

**Format:** string, required, maximum 255 characters.

---

### Description

**For beginners:** an optional field for your own notes. Does not affect processing in any way.

**Format:** free text, optional field.

---

### Trigger token

**For beginners:** the unique word that will appear at the start of every training caption. Pick a meaningless word or letter-digit combination — for example `mychar01` or `xstyle22`. For details, see [Trigger Token](concepts_trigger.md).

**For professionals:** the text anchor that activates the LoRA adapter weights. Must be out-of-distribution relative to the base model — not an ordinary dictionary word. Caption Agent automatically prepends this token to every caption.

**What changes if...**
- Changed after batches with accepted captions exist — already generated captions will keep the old token; consistency is broken.
- Set to an ordinary word — the model already has semantics for it; training will be weaker.

**Format:** string up to 128 characters, no spaces. Default: `p3rs0n4`.

---

### LoRA type

**For beginners:** what you are training. Options: character, style, clothing, face, creature, pose, object. Choose the type that matches your dataset.

**For professionals:** the LoRA type determines which system prompt the normalizer uses and which rule codes are active in the rule checker. For example, for the `style` type, IDENTITY_OVERCAPTION and STYLE_TOKEN checks are disabled — style tokens are acceptable for a style LoRA. For details, see [LoRA Types](concepts_lora_types.md).

**What changes if...**
- Wrong type selected — the normalizer uses an unsuitable prompt; captions may not fit the task.

**Format:** choice from: `character`, `style`, `face`, `clothing`, `creature`, `pose`, `object`. Default: `character`.

---

### Base model family

**For beginners:** the generative model family for which the dataset is being created. For example `flux` or `sdxl`.

**For professionals:** stored as a label in the current version. Active branching of logic by base model is not yet implemented.

**Format:** string. Default: `flux`.

---

### Default source type

**For beginners:** the type of images in new batches in this project. "Synthetic" — generated images. "Reference" — real photos or source references.

**For professionals:** this is the default for new batches; each batch can override it. Source type affects which checks are active: SOURCE_REF_PATTERN_VIOLATION is only enabled for references; SLOT_MISSING is only active for synthetic images.

**Format:** `synthetic` (default) or `reference`.

---

### Default branch

**For beginners:** the purpose of the dataset. "Identity" — the main branch for training a character's identity.

**For professionals:** the branch is passed to the normalizer and checkers. On the `identity` branch, the ADULT_BRANCH_MISMATCH check is active: adult content on this branch is not allowed and should be routed to a separate branch.

**Format:** `identity` (default).

---

### Caption policy

Configurable caption rules for a specific project. Set separately via the "Caption policy" panel on the project page. For details, see [Caption Policy Parameters](ref_policy_params.md).
