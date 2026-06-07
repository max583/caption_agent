# Caption Formats by LoRA Type

The normalizer builds a caption using a slot template that matches the project's LoRA type. The trigger token is required for all types and always comes first.

---

## character

```
{trigger_token}, [framing], [view], wearing [clothing], [pose/action], [expression], [lighting], [setting]
```

| Slot | Content |
|---|---|
| framing | Crop type: portrait, upper-torso, medium shot, fullbody |
| view | Camera angle: front, three-quarter left/right, profile left/right, back, overhead, low angle |
| clothing | All visible garments listed; one attribute per item |
| pose/action | Pose or action: standing, sitting, walking, etc. |
| expression | Facial expression: neutral, slight smile, serious, concentrated, etc. |
| lighting | Lighting type: natural daylight, overcast light, side-lit, etc. |
| setting | Environment in 2–4 words: place category, no specific details |

> **Note:** for character, detailed clothing description is undesirable — each garment gets at most one attribute to avoid binding a specific clothing style to the trigger token.

---

## face

```
{trigger_token}, [framing], [view], [expression], [lighting on face], [clothing fragment (optional)], [setting (optional)]
```

| Slot | Content |
|---|---|
| framing | Crop type: portrait, upper-torso |
| view | Camera angle (same values as character) |
| expression | Facial expression — the primary slot |
| lighting on face | Lighting on the face: directional, even, side-lit |
| clothing fragment | Visible clothing edge only (collar, T-shirt hem) — optional |
| setting | Environment — optional |

---

## pose

```
{trigger_token}, [framing], [view], [pose/action description], [clothing (brief, optional)], [setting (optional)]
```

| Slot | Content |
|---|---|
| framing | Crop type |
| view | Camera angle |
| pose/action | Detailed pose description — primary slot: what the subject is doing, arm/leg/torso positions |
| clothing | Brief garment list with no attributes — optional |
| setting | Environment — optional |

> **Note:** for pose the pose itself is the main content of the caption; clothing and setting are secondary context.

---

## style

```
{trigger_token}, [style_descriptor], [medium_technique], [color_palette], [lighting_mood], [texture_quality], [subject_matter]
```

| Slot | Content |
|---|---|
| style_descriptor | Overall rendering approach: painterly, photographic, illustrative, cel-shaded, etc. |
| medium_technique | Medium and technique: oil painting, digital painting, watercolor, charcoal, etc. |
| color_palette | Dominant colours and tonal character in 3–8 words |
| lighting_mood | Light quality and mood: soft diffused, dramatic chiaroscuro, golden hour warmth, etc. |
| texture_quality | Surface texture: fine grain, visible brushstrokes, smooth blended transitions, etc. |
| subject_matter | What is depicted — brief and generic: landscape, portrait of a figure, still life |

> **Note:** style has no framing, camera angle, age, clothing, or setting. The caption describes visual technique only.

---

## clothing

```
{trigger_token}, [garment_type], [cut_silhouette], [material], [color], [details (key ones)], [how_worn], [wearer_context (optional)]
```

| Slot | Content |
|---|---|
| garment_type | What the garment is: jacket, coat, dress, trousers, hoodie, etc. |
| cut_silhouette | Cut and silhouette: slim fit, oversized, A-line, wrap, boxy, etc. |
| material | Visible material: denim, wool, leather, cotton, knit, etc. |
| color | Dominant colour in 2–4 words |
| details | Visible construction details: collar type, closure, pockets, hardware |
| how_worn | How it is worn: buttoned up, open over a shirt, belted, partially unzipped |
| wearer_context | Wearer body type as a fit reference in 2–4 words — optional |

> **Note:** for clothing each garment attribute is a separate slot — detail is the goal. The wearer is fit context only; face, age, and name are not mentioned.

---

## creature

```
{trigger_token}, [framing], [view], [body_covering or outfit], [pose/action], [expression_or_behavior], [lighting], [setting]
```

| Slot | Content |
|---|---|
| framing | Crop type |
| view | Camera angle |
| body_covering | Natural covering with colour (feral); clothing (anthropomorphic); or both |
| pose/action | Pose or action |
| expression_or_behavior | Expression or behavioural signal: alert, snarling, calm, curious |
| lighting | Lighting |
| setting | Environment |

---

## object

```
{trigger_token}, [object_type], [material], [colour], [notable_details (key ones)], [scale_placement (optional)], [context (optional)]
```

| Slot | Content |
|---|---|
| object_type | What the object is: vase, sword, chair, lamp, helmet, etc. |
| material | Primary visible material: wood, metal, ceramic, leather, etc. |
| colour | Dominant colour |
| notable_details | Key visible construction and decorative details |
| scale_placement | Object position and scale in frame — optional |
| context | The surface or environment in 2–4 words — optional |

> **Note:** object has no framing or camera angle. The caption describes the object, not the camera setup.
