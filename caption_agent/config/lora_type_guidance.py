"""lora_type-specific guidance text for LLM prompts (D-109 Track B, D-114).

get_lora_type_guidance() returns type-specific prose injected into normalizer
and checker prompts via the {lora_type_guidance} placeholder.  This is a code-level
function, not user-configurable — it is derived from the stable LoraType enum.
"""
from __future__ import annotations

_GUIDANCE: dict[str, str] = {
    "character": (
        "This is a character identity LoRA. Focus on: face, pose, clothing, expression, "
        "setting. Do NOT describe stable identity traits (eye colour, nose shape, hair colour) "
        "in standard captions — these bind via visual repetition, not caption text."
    ),
    "creature": (
        "This is a creature identity LoRA. The learning target is the creature's identity — "
        "its species, body form, and physical presence — NOT the background, setting, or accessories. "
        "Caption slots: framing, view, body covering (type and general colour only), pose/action, "
        "expression or behavioral signal, lighting, setting. "
        "Anatomical identity traits (specific eye colour, exact fur or scale pattern, marking shape) "
        "must NOT appear in standard captions — they bind via visual repetition, not caption text. "
        "Use covering type and general colour: 'grey wolf fur', 'dark green scales', 'orange tabby fur'. "
        "For anthropomorphic creatures that wear clothing, apply the same garment-description rules "
        "as character captions (D-095): one attribute per garment. "
        "Dataset risk — setting binding: if all images share the same environment (always forest, "
        "always cave), the LoRA will associate the creature with that setting. "
        "Vary setting, lighting, and pose across the dataset. "
        "Dataset risk — expression uniformity: if most images show the same behavioral state "
        "(always alert, always neutral), the LoRA will treat that state as the creature's default. "
        "Caption the actual expression/behavior and flag datasets that lack variety."
    ),
    "style": (
        "This is a style/aesthetic LoRA. The learning target is the visual treatment — "
        "rendering approach, medium, colour palette, light quality, texture — NOT the subject depicted. "
        "Style-describing words (painterly, photorealistic, cinematic, illustrative) are REQUIRED "
        "in style captions — they are the training signal, not pollution. "
        "Quality boosters (masterpiece, 8k, stunning, gorgeous, award-winning) are FORBIDDEN — "
        "they are marketing tags with no style information. "
        "Do NOT anchor captions to named persons, real places, or named artworks — use generic "
        "subject terms (\"landscape\", \"portrait of a figure\", \"still life\"). "
        "Dataset risk — subject binding: if all images share the same subject type (e.g. always "
        "portraits, always forests), the LoRA will bind the style to that subject. "
        "Captions should reflect subject variety. Flag low variety in subject_matter, "
        "lighting_mood, or medium_technique as a dataset composition concern."
    ),
    "clothing": (
        "This is a clothing/outfit LoRA. The learning target is the garment — its type, cut, "
        "material, colour, construction details, and how it is worn. "
        "Garment detail is REQUIRED: each attribute (cut, material, colour, construction) belongs "
        "in its own caption slot. The character LoRA rule of one attribute per garment (D-095) "
        "is inverted here — detailed multi-attribute garment description is correct and expected. "
        "The wearer is fit context only: note gender presentation and body type briefly if relevant, "
        "then stop. Do NOT describe the wearer's face, age, skin, or identity. "
        "Quality/aesthetic judgments (elegant, stylish, beautiful) are FORBIDDEN — describe "
        "physical properties (cut, material, fabric behaviour) instead. "
        "Dataset risk — wearer binding: if all images show the same body type or the same person, "
        "the LoRA will associate the garment with that wearer. "
        "Dataset risk — styling uniformity: if all images show the garment in the same wearing state "
        "(always buttoned, always belted), the LoRA will not generalise to other wearing modes. "
        "Captions should reflect variety in how_worn, wearer body type, and setting where applicable."
    ),
    "pose": (
        "This is a pose/action LoRA. The learning target is body posture and movement — "
        "limb positions, weight distribution, torso orientation, and action dynamics. "
        "Required caption slots: framing, view, and a detailed pose/action description. "
        "The pose slot must go beyond a single word: name limb positions, weight distribution, "
        "and movement vector (e.g. 'sprinting, left arm forward, right knee raised, strong forward lean'). "
        "Optional slots: brief clothing type (one token per garment, no attributes), coarse setting. "
        "Do NOT describe expression, lighting, or stable identity traits — these are not the training target. "
        "Dataset risk — pose uniformity: if most images show standing poses, the LoRA will not "
        "generalise to dynamic actions. Vary action type, weight distribution, and camera angle. "
        "Dataset risk — angle uniformity: if all images are front view, the LoRA will not transfer "
        "to profile or back views. Flag datasets that lack variety in pose type or camera angle."
    ),
    "object": (
        "This is an object LoRA. The learning target is the physical object — its type, form, "
        "material, surface finish, colour, and construction details. "
        "Required caption slots: object type, material, colour. "
        "Optional slots: notable details (key visible features), scale/placement, context (coarse). "
        "Do NOT include framing or camera angle tokens — camera setup is not the training target. "
        "Describe people only as incidental context ('held by a hand'); they are not the subject. "
        "Style and quality judgments (elegant, beautiful, realistic) are FORBIDDEN — "
        "describe physical properties instead (polished, weathered, carved, lacquered). "
        "Dataset risk — context binding: if all images show the object on the same surface or "
        "in the same environment, the LoRA will associate the object with that context. "
        "Vary placement, lighting, and background across the dataset. "
        "SETTING_OVERSPECIFIC applies: context must be a coarse category name, not specific "
        "surface textures or recurring background objects."
    ),
    "face": (
        "This is a face/portrait LoRA. The learning target is the face — expression, "
        "framing, camera angle, and quality of light on the face. "
        "Required caption slots: framing token, view token, expression, lighting on face. "
        "Optional slots: visible clothing fragment (only if a collar or edge is in frame), "
        "pose modifier (only if distinctly unusual, e.g. 'head tilted left'), "
        "setting (only if it is a deliberate controlled variable). "
        "Do NOT require clothing, pose, or setting — their absence is correct for portrait captions. "
        "Dataset risk — expression uniformity: if most images show neutral expression, "
        "the LoRA will treat neutral as the default face state. "
        "Caption expressions accurately and flag datasets that lack variety in expression or lighting. "
        "For a face LoRA of a specific person: stable identity traits (eye colour, facial structure, "
        "skin tone) must NOT appear in standard captions — they bind via visual repetition, not text. "
        "Anchor-subset captions for specific traits are opt-in only."
    ),
}


def get_lora_type_guidance(lora_type: str) -> str:
    """Return the lora_type-specific prompt guidance text.

    Unknown lora_type values fall back to character guidance rather than crashing.
    """
    return _GUIDANCE.get(lora_type, _GUIDANCE["character"])
