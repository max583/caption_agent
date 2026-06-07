# Analyst Output Schemas by LoRA Type

The analyst returns JSON with different fields depending on the project's LoRA type. Fields common to all types are described once; then the unique fields for each type follow.

## Common fields (all types)

| Field | Type | Content |
|---|---|---|
| `raw_description` | string | Free-text image description in 1–3 sentences |
| `defects` | list | Generation artefacts, anatomy errors, image quality issues |
| `uncertainty_notes` | list | What the analyst could not determine unambiguously |

---

## character

Focus: the character's body and face, pose, clothing, environment.

| Field | Content |
|---|---|
| `pose` | Pose or action: standing, walking, sitting, etc. |
| `camera_angle` | Angle: front, three-quarter left/right, profile left/right, back, overhead, low angle |
| `crop` | Crop type: portrait, upper-torso, medium shot, fullbody |
| `clothing` | All visible garment components listed. For cropped portraits — "bare shoulders visible" or "clothing not in frame" |
| `expression` | Facial expression: neutral, slight smile, serious, concentrated, etc. |
| `setting` | Environment in 2–4 words: place category, no specific details |
| `other_characters` | Other characters visible in the image |
| `adult_context` | Boolean: explicit adult content present |

---

## face

Focus: the face, expression, portrait characteristics. Body and clothing are secondary.

| Field | Content |
|---|---|
| `pose` | Head orientation or visible body pose; "not visible" if body is out of frame |
| `camera_angle` | Angle (same values as character) |
| `crop` | Crop type |
| `expression` | Facial expression |
| `skin_tone` | Skin tone on a 6-level scale: fair / light / medium / olive / tan / dark / deep |
| `facial_structure` | Face shape: oval, round, square, heart-shaped, angular, narrow, wide |
| `eye_detail` | Eye colour and shape if clearly visible |
| `facial_hair` | Facial hair: clean-shaven, stubble, short beard, full beard, etc. |
| `clothing` | Visible clothing fragment only (collar, T-shirt edge). "clothing not in frame" if none |
| `setting` | Environment in 2–4 words |
| `other_characters` | Other people in the image |
| `adult_context` | Boolean |

---

## pose

Focus: precise body position and movement. Clothing and setting are brief context.

| Field | Content |
|---|---|
| `pose_action` | Primary field. Detailed description: what the subject is doing, torso orientation, arm positions, leg positions, weight distribution, movement direction |
| `body_silhouette` | Overall silhouette: compact, spread, diagonal, dynamic, S-curve, etc. |
| `camera_angle` | Angle |
| `crop` | Crop type |
| `clothing` | Brief list of visible garments — one token per item, no attributes |
| `setting` | Environment in 2–4 words |
| `other_characters` | Other characters |
| `adult_context` | Boolean |

---

## style

Focus: visual technique and artistic treatment. The subject is secondary; do not name specific real people or places.

| Field | Content |
|---|---|
| `style_descriptor` | Overall rendering approach: painterly, photographic, illustrative, cel-shaded, woodblock print, etc. |
| `medium_technique` | Apparent medium and technique: oil painting, digital painting, photography, watercolor, charcoal, etc. |
| `color_palette` | Dominant colours and tonal character in 3–8 words |
| `lighting_mood` | Light quality and mood: soft diffused, dramatic chiaroscuro, golden hour warmth, etc. |
| `texture_quality` | Surface texture: fine grain, visible brushstrokes, smooth blended transitions, etc. |
| `subject_matter` | What is depicted — brief and generic: landscape, portrait of a figure, still life, street scene |

> **Note:** type=style has no `camera_angle`, `crop`, `other_characters`, `adult_context`, or `setting` fields. The analyst only describes the visual treatment.

---

## clothing

Focus: the garment itself — cut, material, colour, construction, how it is worn. The wearer is context for fit assessment.

| Field | Content |
|---|---|
| `garment_type` | What the garment is: jacket, coat, dress, trousers, hoodie, blazer, etc. |
| `cut_silhouette` | Cut and silhouette: slim fit, relaxed fit, oversized, A-line, wrap, boxy, etc. |
| `material` | Visible material: denim, wool, leather, cotton, silk, knit, etc. |
| `color` | Dominant colour and tone in 2–4 words |
| `details` | Visible construction details: collar type, closure, pockets, seams, hardware |
| `fabric_behavior` | How the fabric behaves: stiff and structured, softly draped, flowing, wrinkled, crisp |
| `how_worn` | How it is worn: buttoned up, open over a shirt, belted, tucked in, partially unzipped |
| `wearer_context` | Minimal wearer context as a fit reference in 2–4 words: slim male frame, curvy female figure. Body type only — no face, age, or personal characteristics |
| `setting` | Environment in 2–4 words |
| `other_characters` | Other people in the image |
| `adult_context` | Boolean |

---

## creature

Focus: creature type, pose, body covering, distinctive anatomical features. Supports both feral and anthropomorphic creatures.

| Field | Content |
|---|---|
| `creature_type` | Species: wolf, dragon, cat, fox, anthropomorphic fox, etc. |
| `pose` | Pose or action: standing, crouching, flying, prowling, etc. |
| `camera_angle` | Angle |
| `crop` | Crop type |
| `body_covering` | Natural covering (fur, scales, feathers) with colour and pattern; or worn clothing for anthropomorphic creatures; or both |
| `distinctive_features` | Non-standard anatomical features: horns, antlers, tail, wings, mane, beak, markings, etc. |
| `expression_or_behavior` | Facial expression or behavioural signal: alert, snarling, calm, curious, playful |
| `setting` | Environment in 2–4 words |
| `other_characters` | Other creatures or people |
| `adult_context` | Boolean |

---

## object

Focus: the object's form, material, surface, and details. People in the image are secondary context.

| Field | Content |
|---|---|
| `object_type` | What the object is: chair, vase, sword, bag, lamp, helmet, etc. |
| `form_shape` | Geometric form and proportions: cylindrical, rectangular, curved, tapered, etc. |
| `material` | Primary visible material: wood, metal, ceramic, leather, glass, etc. |
| `surface_finish` | Surface quality: polished, matte, weathered, scratched, textured, rusted, etc. |
| `color` | Dominant colour and tone |
| `notable_details` | Visible construction and decorative details: carved relief, brass fittings, stitched seam, etc. |
| `scale_placement` | Object position and scale in frame: centred, tilted, hanging, filling frame, etc. |
| `context` | The surface or environment in 2–4 words: wooden shelf, stone floor, white studio |
| `other_characters` | People or creatures in the image |
| `adult_context` | Boolean |

> **Note:** type=object uses `context` for the environment field, not `setting` (as in other types).
