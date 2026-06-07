# Форматы подписей по типам LoRA

Нормализатор формирует подпись по шаблону, соответствующему типу LoRA проекта. Trigger token обязателен для всех типов и всегда стоит первым.

---

## character — персонаж

```
{trigger_token}, [framing], [view], wearing [clothing], [pose/action], [expression], [lighting], [setting]
```

| Слот | Содержимое |
|---|---|
| framing | Тип кадрирования: portrait, upper-torso, medium shot, fullbody |
| view | Ракурс: front, three-quarter left/right, profile left/right, back, overhead, low angle |
| clothing | Перечисление видимых предметов одежды; один атрибут на предмет |
| pose/action | Поза или действие: standing, sitting, walking и т.д. |
| expression | Выражение лица: neutral, slight smile, serious, concentrated и т.д. |
| lighting | Тип освещения: natural daylight, overcast light, side-lit и т.д. |
| setting | Обстановка в 2–4 словах: категория места, без деталей |

> **Важно:** для character детальное описание одежды нежелательно — каждый предмет получает не более одного атрибута, чтобы не привязать конкретный стиль одежды к trigger token.

---

## face — лицо/портрет

```
{trigger_token}, [framing], [view], [expression], [lighting on face], [clothing fragment (optional)], [setting (optional)]
```

| Слот | Содержимое |
|---|---|
| framing | Тип кадрирования: portrait, upper-torso |
| view | Ракурс (те же значения, что для character) |
| expression | Выражение лица — основной слот |
| lighting on face | Освещение в отношении лица: directional, even, side-lit |
| clothing fragment | Только видимый край одежды (воротник, край футболки) — опционально |
| setting | Обстановка — опционально |

---

## pose — поза/действие

```
{trigger_token}, [framing], [view], [pose/action description], [clothing (brief, optional)], [setting (optional)]
```

| Слот | Содержимое |
|---|---|
| framing | Тип кадрирования |
| view | Ракурс |
| pose/action | Детальное описание позы — основной слот: что делает субъект, положение рук, ног, торса |
| clothing | Краткий список одежды без атрибутов — опционально |
| setting | Обстановка — опционально |

> **Важно:** для pose поза является главным содержанием подписи; одежда и обстановка — вторичный контекст.

---

## style — стиль

```
{trigger_token}, [style_descriptor], [medium_technique], [color_palette], [lighting_mood], [texture_quality], [subject_matter]
```

| Слот | Содержимое |
|---|---|
| style_descriptor | Общий подход к рендерингу: painterly, photographic, illustrative, cel-shaded и т.д. |
| medium_technique | Техника и материал: oil painting, digital painting, watercolor, charcoal и т.д. |
| color_palette | Доминирующие цвета и тональный характер в 3–8 словах |
| lighting_mood | Свет и настроение: soft diffused, dramatic chiaroscuro, golden hour warmth и т.д. |
| texture_quality | Поверхность: fine grain, visible brushstrokes, smooth blended transitions и т.д. |
| subject_matter | Что изображено — обобщённо: landscape, portrait of a figure, still life |

> **Важно:** у style нет framing, ракурса, возраста, одежды или обстановки. Подпись описывает исключительно визуальную технику.

---

## clothing — одежда/аутфит

```
{trigger_token}, [garment_type], [cut_silhouette], [material], [color], [details (key ones)], [how_worn], [wearer_context (optional)]
```

| Слот | Содержимое |
|---|---|
| garment_type | Тип предмета: jacket, coat, dress, trousers, hoodie и т.д. |
| cut_silhouette | Крой и силуэт: slim fit, oversized, A-line, wrap, boxy и т.д. |
| material | Материал: denim, wool, leather, cotton, knit и т.д. |
| color | Основной цвет в 2–4 словах |
| details | Видимые конструктивные детали: тип воротника, застёжка, карманы, фурнитура |
| how_worn | Как надето: buttoned up, open over a shirt, belted, partially unzipped |
| wearer_context | Телосложение носителя как референс посадки в 2–4 словах — опционально |

> **Важно:** для clothing каждый атрибут предмета одежды является отдельным слотом — детальность желательна. Носитель — только контекст посадки; лицо, возраст, имя не упоминаются.

---

## creature — существо/персонаж-животное

```
{trigger_token}, [framing], [view], [body_covering or outfit], [pose/action], [expression_or_behavior], [lighting], [setting]
```

| Слот | Содержимое |
|---|---|
| framing | Тип кадрирования |
| view | Ракурс |
| body_covering | Натуральный покров с цветом (для феральных); одежда (для антропоморфных); или оба |
| pose/action | Поза или действие |
| expression_or_behavior | Мимика или поведенческий сигнал: alert, snarling, calm, curious |
| lighting | Освещение |
| setting | Обстановка |

---

## object — объект/предмет

```
{trigger_token}, [object_type], [material], [colour], [notable_details (key ones)], [scale_placement (optional)], [context (optional)]
```

| Слот | Содержимое |
|---|---|
| object_type | Тип предмета: vase, sword, chair, lamp, helmet и т.д. |
| material | Основной материал: wood, metal, ceramic, leather и т.д. |
| colour | Основной цвет |
| notable_details | Ключевые видимые детали: отделка, конструктивные элементы |
| scale_placement | Положение объекта в кадре — опционально |
| context | Окружение в 2–4 словах — опционально |

> **Важно:** у object нет framing и ракурса. Подпись описывает предмет, а не условия съёмки.
