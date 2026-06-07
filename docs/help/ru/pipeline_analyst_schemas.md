# Схемы вывода аналитика по типам LoRA

Аналитик возвращает JSON с разными полями в зависимости от типа LoRA проекта. Поля, общие для всех типов, описаны один раз; затем — уникальные поля каждого типа.

## Общие поля (все типы)

| Поле | Тип | Содержимое |
|---|---|---|
| `raw_description` | строка | Свободное описание изображения в 1–3 предложениях |
| `defects` | список | Артефакты генерации, анатомические ошибки, дефекты изображения |
| `uncertainty_notes` | список | Что аналитик не смог определить однозначно |

---

## character — персонаж

Фокус: тело и лицо персонажа, поза, одежда, окружение.

| Поле | Содержимое |
|---|---|
| `pose` | Поза или действие: standing, walking, sitting и т.д. |
| `camera_angle` | Ракурс: front, three-quarter left/right, profile left/right, back, overhead, low angle |
| `crop` | Тип кадрирования: portrait, upper-torso, medium shot, fullbody |
| `clothing` | Перечисление всех видимых элементов одежды. Для кадрированных портретов — «bare shoulders visible» или «clothing not in frame» |
| `expression` | Выражение лица: neutral, slight smile, serious, concentrated и т.д. |
| `setting` | Обстановка в 2–4 словах: категория места, без деталей |
| `other_characters` | Другие персонажи на изображении |
| `adult_context` | Булево: наличие явного взрослого контента |

---

## face — лицо/портрет

Фокус: лицо, мимика, портретные характеристики. Тело и одежда вторичны.

| Поле | Содержимое |
|---|---|
| `pose` | Ориентация головы или видимая поза тела; «not visible» если тело вне кадра |
| `camera_angle` | Ракурс (те же значения, что для character) |
| `crop` | Тип кадрирования |
| `expression` | Выражение лица |
| `skin_tone` | Тон кожи по шкале из 6 значений: fair / light / medium / olive / tan / dark / deep |
| `facial_structure` | Форма лица: oval, round, square, heart-shaped, angular, narrow, wide |
| `eye_detail` | Цвет и форма глаз, если хорошо видны |
| `facial_hair` | Растительность на лице: clean-shaven, stubble, short beard, full beard и т.д. |
| `clothing` | Только видимый фрагмент одежды (воротник, край футболки). «clothing not in frame» если одежды нет |
| `setting` | Обстановка в 2–4 словах |
| `other_characters` | Другие люди на изображении |
| `adult_context` | Булево |

---

## pose — поза/действие

Фокус: точное описание положения тела и движения. Одежда и окружение — краткий контекст.

| Поле | Содержимое |
|---|---|
| `pose_action` | Основное поле. Детальное описание: что делает субъект, ориентация торса, положение рук и ног, распределение веса, направление движения |
| `body_silhouette` | Общий силуэт: compact, spread, diagonal, dynamic, S-curve и т.д. |
| `camera_angle` | Ракурс |
| `crop` | Тип кадрирования |
| `clothing` | Краткий список видимой одежды — один токен на предмет, без деталей |
| `setting` | Обстановка в 2–4 словах |
| `other_characters` | Другие персонажи |
| `adult_context` | Булево |

---

## style — стиль

Фокус: визуальная техника и художественная обработка. Субъект вторичен; конкретных людей и мест не называть.

| Поле | Содержимое |
|---|---|
| `style_descriptor` | Общий подход к рендерингу: painterly, photographic, illustrative, cel-shaded, woodblock print и т.д. |
| `medium_technique` | Техника и материал: oil painting, digital painting, photography, watercolor, charcoal и т.д. |
| `color_palette` | Доминирующие цвета и тональный характер в 3–8 словах |
| `lighting_mood` | Качество света и настроение: soft diffused, dramatic chiaroscuro, golden hour warmth и т.д. |
| `texture_quality` | Поверхностная текстура: fine grain, visible brushstrokes, smooth blended transitions и т.д. |
| `subject_matter` | Что изображено — кратко и обобщённо: landscape, portrait of a figure, still life, street scene |

> **Важно:** у type=style нет полей `camera_angle`, `crop`, `other_characters`, `adult_context`, `setting`. Аналитик работает только с визуальной обработкой.

---

## clothing — одежда/аутфит

Фокус: сам предмет одежды — крой, материал, цвет, конструкция, способ носки. Носитель — контекст для оценки посадки.

| Поле | Содержимое |
|---|---|
| `garment_type` | Что это за предмет: jacket, coat, dress, trousers, hoodie, blazer и т.д. |
| `cut_silhouette` | Крой и силуэт: slim fit, relaxed fit, oversized, A-line, wrap, boxy и т.д. |
| `material` | Видимый материал: denim, wool, leather, cotton, silk, knit и т.д. |
| `color` | Основной цвет и тон в 2–4 словах |
| `details` | Видимые конструктивные детали: тип воротника, застёжка, карманы, швы, фурнитура |
| `fabric_behavior` | Поведение ткани: stiff and structured, softly draped, flowing, wrinkled, crisp |
| `how_worn` | Как надето: buttoned up, open over a shirt, belted, tucked in, partially unzipped |
| `wearer_context` | Минимальный контекст носителя как референс посадки в 2–4 словах: slim male frame, curvy female figure. Только телосложение — без лица, возраста, характеристик |
| `setting` | Обстановка в 2–4 словах |
| `other_characters` | Другие люди на изображении |
| `adult_context` | Булево |

---

## creature — существо/персонаж-животное

Фокус: вид существа, поза, покров, отличительные анатомические черты. Поддерживает как феральных (дикое животное), так и антропоморфных существ.

| Поле | Содержимое |
|---|---|
| `creature_type` | Вид: wolf, dragon, cat, fox, anthropomorphic fox и т.д. |
| `pose` | Поза или действие: standing, crouching, flying, prowling и т.д. |
| `camera_angle` | Ракурс |
| `crop` | Тип кадрирования |
| `body_covering` | Натуральный покров (шерсть, чешуя, перья) с цветом и паттерном, или одежда для антропоморфных, или оба варианта |
| `distinctive_features` | Нестандартные анатомические черты: horns, antlers, tail, wings, mane, beak, markings и т.д. |
| `expression_or_behavior` | Мимика или поведенческий сигнал: alert, snarling, calm, curious, playful |
| `setting` | Обстановка в 2–4 словах |
| `other_characters` | Другие существа или люди |
| `adult_context` | Булево |

---

## object — объект/предмет

Фокус: форма, материал, поверхность, детали предмета. Люди на изображении — вторичный контекст.

| Поле | Содержимое |
|---|---|
| `object_type` | Что это: chair, vase, sword, bag, lamp, helmet и т.д. |
| `form_shape` | Геометрическая форма и пропорции: cylindrical, rectangular, curved, tapered и т.д. |
| `material` | Основной видимый материал: wood, metal, ceramic, leather, glass и т.д. |
| `surface_finish` | Поверхность: polished, matte, weathered, scratched, textured, rusted и т.д. |
| `color` | Основной цвет и тон |
| `notable_details` | Видимые конструктивные и декоративные детали: carved relief, brass fittings, stitched seam и т.д. |
| `scale_placement` | Положение объекта в кадре и его масштаб: centred, tilted, hanging, filling frame и т.д. |
| `context` | Окружение или поверхность в 2–4 словах: wooden shelf, stone floor, white studio |
| `other_characters` | Люди или существа на изображении |
| `adult_context` | Булево |

> **Важно:** у type=object поле окружения называется `context`, не `setting` (как у других типов).
