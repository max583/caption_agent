"""UI translation strings (D-107). Dict-based, no external dependencies.

Usage in templates:
    {{ t['key'] }}          — translate a key
    {{ t.get('key', '') }}  — translate with empty fallback (safe for optional keys)

The pipeline always uses English for captions, logs, and warning messages.
Only UI labels, button text, and warning code labels are translated here.
"""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        # Nav
        "nav_projects":    "Проекты",
        "nav_settings":    "Настройки",
        "nav_journal":     "Журнал",
        "nav_help":        "Справка",
        "help_not_found":  "Раздел в разработке",
        "nav_lang_switch": "EN",
        # Batch form tabs
        "tab_overview": "Обзор",
        "tab_items":    "Items",
        "tab_review":   "Ревью",
        # Decision buttons
        "btn_accept":     "Принять",
        "btn_regenerate": "Регенерировать",
        "btn_drop":       "Отклонить",
        "btn_skip":       "Пропустить",
        # Common buttons / labels
        "btn_save":            "Сохранить",
        "btn_cancel":          "Отмена",
        "btn_refresh":         "Обновить",
        "btn_create":          "Создать",
        "btn_delete":          "Удалить",
        "lbl_warnings":        "Предупреждения",
        "lbl_caption":         "Caption",
        "lbl_error":           "Ошибка",
        "lbl_state":           "Состояние",
        "lbl_file":            "Файл",
        "lbl_decision":        "Решение",
        "lbl_all":             "Все",
        "lbl_filter":          "Фильтр",
        "lbl_no_items":        "Нет items.",
        "lbl_no_items_filter": "Нет items под выбранным фильтром.",
        # Projects list
        "page_projects":       "Проекты",
        "btn_create_project":  "Создать проект",
        "lbl_no_projects":     "Нет проектов.",
        # Settings
        "settings_ui_section":  "UI",
        "settings_ui_language": "Язык интерфейса",
        # Navigation / breadcrumbs
        "lbl_back":             "← Назад",
        "lbl_back_to_list":     "← Назад в список",
        "lbl_projects_breadcrumb": "Проекты",
        # Batch form — Overview tab
        "lbl_items_by_state":   "Items по состоянию",
        "lbl_no_items_scan":    "Нет items. Нажмите «Сканировать» для поиска изображений.",
        "lbl_state_history":    "История состояний",
        "lbl_state_history_empty": "История пуста",
        "lbl_errors_section":   "Ошибки",
        "lbl_select_item_review": "Выберите item из списка слева",
        # Batch lifecycle
        "btn_pause":            "Поставить на паузу",
        "btn_resume":           "Возобновить",
        "btn_abort":            "Прервать",
        "btn_export":           "Экспортировать",
        "btn_scan":             "🔍 Сканировать",
        "btn_reprocess":        "↻ Обработать повторно",
        "btn_retry_errors":     "↻ Retry ошибок",
        "btn_edit_schedule":    "Изменить расписание",
        "btn_open_review":      "Открыть ревью",
        "btn_open":             "Открыть",
        "lbl_action_done":      "выполнен",
        "lbl_scan_complete":    "Сканирование завершено",
        "lbl_error_generic":    "Ошибка",
        "lbl_saved":            "Сохранено",
        "lbl_batch_deleted":    "Batch удалён",
        # Batch items tab
        "lbl_selected_count":   "Выбрано:",
        "lbl_mass_actions":     "Массовые действия ▾",
        "lbl_mass_accept":      "Принять выбранные",
        "lbl_mass_drop":        "Отклонить выбранные",
        "lbl_mass_skip":        "Пропустить выбранные",
        "lbl_mass_regen":       "Регенерировать выбранные",
        "lbl_include_warnings": "Включить items с предупреждениями в Accept",
        "lbl_warn_count":       "предупр.",
        "lbl_gen_prompt":       "Промпт генерации:",
        "btn_open_in_review":   "Открыть в Review →",
        # Item detail
        "lbl_caption_not_ready": "Caption не готов",
        "lbl_warnings_detail":  "Предупреждения",
        "lbl_gen_context":      "Контекст генерации",
        "lbl_candidate_prompts": "Промпты из метаданных (справка)",
        "lbl_analyst_output":   "Вывод аналитика (VLM)",
        "lbl_select_item":      "Выберите item из списка",
        # Batch header
        "lbl_queued_state":     "В очереди...",
        "lbl_scanning_state":   "Сканирование...",
        "lbl_processing_count": "в работе",
        "lbl_errors_count":     "ошибок",
        "lbl_awaiting_count":   "ждут",
        "lbl_review_short":     "ревью",
        "lbl_scanning_progress": "Сканирование",
        "lbl_schedule_label":   "Расписание:",
        # Batch cards
        "lbl_scheduled_at":     "По расписанию @",
        "lbl_no_batches":       "Батчей нет.",
        "lbl_approved_short":   "принято",
        # Project card
        "lbl_errors_batches":   "ошибок",
        "lbl_awaiting_review":  "ждут ревью",
        "lbl_active_batches":   "активных",
        "lbl_no_batches_card":  "нет батчей",
        # Server summary
        "lbl_total_projects":   "Проектов:",
        "lbl_active_batches_sum": "Активных батчей:",
        "lbl_awaiting_review_sum": "Ожидают ревью:",
        "lbl_scheduled_sum":    "По расписанию:",
        "lbl_errors_sum":       "Ошибки:",
        "lbl_queue_depth":      "Очередь:",
        # Projects list
        "btn_create_first":     "+ Создать первый проект",
        "lbl_create_project_title": "Создать проект",
        "lbl_name_field":       "Название *",
        "lbl_description_field": "Описание",
        "lbl_desc_placeholder": "Краткое описание...",
        "lbl_loading_create":   "Создаю...",
        "lbl_name_required_err": "Название обязательно",
        "lbl_create_error":     "Ошибка создания",
        # Project workspace
        "lbl_no_description":   "Нет описания",
        "lbl_type_label":       "Тип:",
        "lbl_output_label":     "Вывод:",
        "lbl_created_label":    "Создан:",
        "lbl_name_label":       "Название",
        "lbl_description_label": "Описание",
        "btn_edit":             "Изменить",
        "lbl_batches_section":  "Батчи",
        "btn_project_logs":     "📋 Логи проекта",
        "btn_create_batch":     "+ Создать batch",
        "lbl_trigger_token_hint": "Уникальный токен для этой LoRA. Используется во всех каптионах.",
        "lbl_lora_type":          "Тип LoRA",
        "lbl_base_model_family":  "Базовая модель",
        "lbl_base_model_hint":    "Например: flux, sdxl, sd15, hunyuan",
        "lora_type_character":    "character — персонаж",
        "lora_type_creature":     "creature — существо",
        "lora_type_style":        "style — стиль",
        "lora_type_clothing":     "clothing — одежда",
        "lora_type_pose":         "pose — поза",
        "lora_type_object":       "object — объект",
        "lora_type_face":         "face — лицо",
        "lbl_create_batch_title": "Создать batch",
        "lbl_images_folder":    "Папка с изображениями *",
        "lbl_source_type":      "Тип источника",
        "lbl_branch_label":     "Ветка",
        "lbl_schedule_optional": "Запустить по расписанию (необязательно)",
        "lbl_browse":           "📁 Обзор…",
        "lbl_folder_picker_title": "Выбор папки",
        "btn_go":               "Перейти",
        "btn_up":               "⬆ Вверх",
        "lbl_loading":          "Загружаю…",
        "lbl_no_subdirs":       "Подпапок нет.",
        "lbl_dblclick_hint":    "Двойной клик — войти в папку. Клик — выбрать.",
        "btn_select_folder":    "Выбрать эту папку",
        "lbl_required_name_folder": "Название и папка обязательны",
        "lbl_settings_title":   "Настройки",
        # Journal
        "page_journal":         "Журнал",
        "lbl_level_filter":     "Уровень",
        "lbl_project_filter":   "Проект",
        "lbl_date_from":        "Дата с",
        "lbl_date_to":          "Дата до",
        "lbl_search_label":     "Поиск",
        "lbl_search_placeholder": "Текст...",
        "btn_apply_filters":    "Применить",
        "btn_reset_filters":    "Сбросить",
        "btn_delete_filtered":  "🗑 Удалить отфильтрованные",
        "lbl_journal_time":     "Время",
        "lbl_journal_level":    "Уровень",
        "lbl_journal_event":    "Событие",
        "lbl_journal_message":  "Сообщение",
        "lbl_journal_empty":    "Журнал пуст.",
        "lbl_journal_prev":     "← Пред.",
        "lbl_journal_next":     "След. →",
        "lbl_journal_page":     "Стр.",
        "lbl_journal_of":       "из",
        # Settings — section names (sidebar + headings)
        "settings_section_retry":    "Retry & Errors",
        "settings_section_polling":  "Опрос (секунды)",
        "settings_section_paths":    "Пути и хранилище",
        "settings_section_logging":  "Логирование",
        "settings_section_database": "База данных",
        # Settings — saved/applied indicators
        "lbl_saved_indicator":  "✓ Сохранено",
        "lbl_applied_indicator":"✓ Применено",
        "lbl_overrides_cleared": "Overrides сброшены",
        "lbl_save_error":        "Ошибка сохранения",
        # Settings — Retry section
        "settings_normalizer_retries":       "Макс. self-retries нормализатора",
        "settings_consecutive_threshold":    "Порог последоват. ошибок (стоп batch)",
        # Settings — Polling section
        "settings_poll_projects_list":       "Список проектов",
        "settings_poll_project_workspace":   "Workspace проекта",
        "settings_poll_batch_processing":    "Batch в Processing",
        "settings_poll_batch_idle":          "Batch в Idle/Done",
        # Settings — Logging section
        "settings_log_level":       "Уровень логирования",
        "settings_log_retention":   "Business log retention (дней)",
        "settings_log_enable":      "Включить",
        # Settings — Paths section
        "settings_bootstrap_hint":   "Bootstrap paths (из env / config.toml, не редактируются через UI):",
        "settings_host_port":        "сервер хост/порт",
        "settings_data_dir":         "папка данных",
        # Settings — Database section
        "settings_db_conn_hint":     "Строка подключения задаётся через env-переменную",
        "settings_db_default_hint":  "по умолчанию: SQLite в папке data/",
        "settings_db_integrity":     "Проверка целостности БД",
        "settings_db_integrity_desc":"Запускает проверку FK-связей и подсчёт аномальных состояний.",
        "settings_db_run_check":     "🔍 Запустить проверку",
        "settings_db_admin":         "Администрирование",
        "settings_db_admin_desc":    "Перезапуск применяет изменения кода или конфигурации без ручного вмешательства в терминал.",
        "settings_db_restart":       "↺ Перезапустить сервер",
        # Settings — per-step overrides
        "settings_clear_overrides":  "↺ Сбросить все overrides",
        "lbl_hide":                  "Скрыть",
        "lbl_show":                  "Показать",
        "lbl_reset_to_main":         "Сбросить к основному",
        # Settings — LLM profiles JS
        "lbl_profile_activated":     "Профиль активирован — страница перезагружается",
        "lbl_activation_error":      "Ошибка активации",
        "lbl_request_error":         "Ошибка запроса",
        "confirm_delete_profile":    "Удалить профиль?",
        "lbl_cannot_delete_active":  "Нельзя удалить активный профиль — сначала переключитесь",
        "lbl_delete_error":          "Ошибка удаления",
        "lbl_profile_exists":        "Профиль с таким именем уже существует",
        "lbl_name_taken":            "Такое имя уже занято",
        "lbl_rename_error":          "Ошибка переименования",
        "lbl_profile_not_selected":  "Профиль не выбран",
        # Settings — restart / integrity check JS
        "lbl_sending_request":       "Отправляю запрос...",
        "lbl_server_restarting":     "Сервер перезапускается. Страница обновится через 4 секунды...",
        "lbl_restart_error_prefix":  "Ошибка: ",
        "lbl_unknown_error":         "неизвестная ошибка",
        "lbl_connection_error_restart": "Ошибка соединения. Возможно, сервер уже перезапускается — обновите страницу вручную.",
        "lbl_checking":              "Проверяю...",
        # Journal JS
        "confirm_delete_logs":       "Удалить {n} записей?",
        "lbl_deleted_count":         "Удалено: ",
        # Settings — remaining
        "settings_lbl_profiles":   "Профили LLM",
        "settings_select_profile": "— выберите профиль —",
        "btn_activate":         "Активировать",
        "btn_test_connection":  "🔌 Тест",
        "btn_rename":           "Переименовать",
        "lbl_no_profiles_hint": "Профилей пока нет — сохраните текущий конфиг как первый профиль:",
        "btn_save_as_profile":  "+ Сохранить текущий конфиг как профиль…",
        "lbl_new_profile_title": "Новый профиль",
        "lbl_profile_name":     "Название",
        "lbl_profile_desc":     "Описание (необязательно)",
        "lbl_rename_profile_title": "Переименовать профиль",
        "lbl_llm_main_config":  "LLM — основная конфигурация",
        "lbl_llm_per_step":     "Per-step LLM overrides",
        "lbl_check_connection": "🔌 Проверить соединение",
        # Base JS
        "js_server_error":      "Ошибка сервера: ",
        "js_connection_lost":   "Соединение прервано",
        # ETA / time display
        "eta_computing":        "вычисляю…",
        "eta_soon":             "скоро",
        "lbl_time_min":         "м",
        "lbl_time_sec":         "с",
        # Analysis panel (D-108)
        "lbl_analysis_title":    "Анализ датасета",
        "lbl_analysis_total":    "Итого items:",
        "lbl_analysis_approved": "Принято:",
        "lbl_analysis_awaiting": "Ожидают ревью:",
        "lbl_analysis_framing":  "Framing",
        "lbl_analysis_view":     "View",
        "lbl_analysis_clothing": "Состояние одежды",
        "lbl_analysis_source_type": "Тип источника",
        "lbl_analysis_warnings": "Предупреждения",
        "lbl_analysis_pose":      "Поза",
        "lbl_analysis_per_batch": "По батчам",
        "lbl_analysis_no_items": "Нет APPROVED/AWAITING_REVIEW items в этом проекте.",
        "lbl_analysis_recommendations": "Рекомендации",
        "lbl_analysis_recs_healthy": "Датасет выглядит сбалансированным — рекомендаций нет.",
        "lbl_analysis_llm_unavailable": "LLM анализ недоступен — проверьте Settings → LLM или логи сервера.",
        # Warning code labels (code → human-readable label for the UI)
        "warn_TRIGGER_MISSING":              "Отсутствует trigger-токен",
        "warn_FRAMING_INVALID":              "Неверный framing",
        "warn_VIEW_INVALID":                 "Неверный view",
        "warn_STYLE_TOKEN":                  "Style-токен",
        "warn_AGE_PHRASE":                   "Фраза возраста",
        "warn_NEGATIVE_WORDING":             "Отрицательная формулировка",
        "warn_IDENTITY_OVERCAPTION":         "Overcaption идентичности",
        "warn_NUDE_ON_CROPPED_PORTRAIT":     "Nude на кропе",
        "warn_SOURCE_REF_PATTERN_VIOLATION": "Нарушение шаблона source ref",
        "warn_ADULT_BRANCH_MISMATCH":        "Несоответствие ветки adult",
        "warn_MULTI_CHARACTER":              "Несколько персонажей",
        "warn_SLOT_MISSING":                 "Отсутствует слот",
        "warn_SETTING_OVERSPECIFIC":         "Сеттинг слишком конкретный",
        "warn_CLOTHING_OVERDESCRIBED":       "Одежда описана слишком подробно",
        "warn_GAP_FILLED_FROM_PROMPT":       "Слот заполнен из промпта (проверить)",
        "warn_GAP_UNFILLABLE":               "Слот не удалось заполнить",
        # Caption policy (D-114)
        "lbl_caption_policy":              "Caption Policy",
        "lbl_identity_trait_patterns":     "Паттерны идентичности (regex)",
        "lbl_setting_overspecific_phrases":"Запрещённые фразы сеттинга",
        "lbl_source_ref_setting":          "Токен сеттинга source-ref",
        "lbl_coarse_setting_note":         "Правило coarse setting",
        "lbl_custom_normalizer_rules":     "Доп. правила normalizer'а",
        "lbl_custom_checker_rules":        "Доп. правила checker'а",
        "lbl_policy_using_defaults":       "Используются дефолты проекта (caption_policy не задан)",
        "btn_save_policy":                 "Сохранить policy",
        "btn_reset_policy":                "Сбросить к дефолтам",
        "lbl_for_experts": "▸ Для опытных пользователей",
        # Caption policy — 4-part help texts
        "help_identity_patterns_what":
            "Список фраз, которые запрещены в подписях к обучающим изображениям вашего персонажа."
            " Объясним на примере: допустим, в каждой подписи написано «серые глаза»."
            " Тогда модель выучивает цвет глаз через текст, а не через визуальный образ."
            " На практике это означает: если при генерации вы не написали «gray eyes» в запросе —"
            " персонаж может получить произвольный цвет глаз, потому что визуально эта черта не закрепилась."
            " Если же вы исключите «серые глаза» из всех подписей — модель выучит этот цвет только"
            " по картинкам, и персонаж будет рисоваться с серыми глазами автоматически, без упоминания в запросе.",
        "help_identity_patterns_how":
            "Перечислите все такие признаки вашего персонажа, чтобы привязать их к нему автоматически."
            " Вводите по одному выражению на строку. Можно писать обычными словами: gray eyes, distinctive nose —"
            " система найдёт их в любом месте подписи. Для гибкого поиска допустимы регулярные выражения:"
            " gray eyes(?: clearly visible)? найдёт оба варианта."
            " Пустой список — проверка отключена. Чем длиннее список, тем строже фильтр.",
        "help_identity_patterns_expert":
            "В LoRA-датасете черты внешности в подписях создают нежелательную text-visual корреляцию:"
            " если «серые глаза» встречаются в 80% подписей, модель привязывает эту фразу к trigger token"
            " и воспроизводит её без явного промпта. Идентичность должна закрепляться через визуальное"
            " повторение, а не через текстовое совпадение — иначе теряется управляемость."
            " Приложение автоматически проверяет каждую подпись и отправляет её на переформулировку,"
            " не давая описаниям внешности просочиться в датасет.",
        "help_identity_patterns_tech":
            "Один regex-паттерн на строку. Используется rule_checker для IDENTITY_OVERCAPTION.",
        "help_setting_phrases_what":
            "Список фраз, которые запрещены при описании фона. Объясним на примере: изображения для"
            " обучения сгенерированы в разных локациях, но на многих из них есть деревянные здания, брёвна,"
            " заборы. Одно изображение подписывается «wooden building», другое — «log cabin», третье —"
            " «wooden fence». Каждое слово разное, но все они постепенно привязывают персонажа к деревянным"
            " постройкам. Если заменить все эти конкретные описания на нейтральное «outdoor setting» —"
            " персонаж остаётся без жёсткого фона: вы сможете поместить его куда угодно одним словом в промпте."
            " То есть речь идёт о замене конкретных описаний общими, не дающими возможности привязать образ"
            " к конкретным окружающим предметам.",
        "help_setting_phrases_how":
            "Перечислите конкретные детали фона, которые ЧАСТО встречаются на ваших обучающих изображениях:"
            " материалы, архитектурные элементы, характерные объекты. Вводите по одной фразе на строку —"
            " система найдёт их в любом месте подписи и попросит ИИ заменить описание более общим."
            " Пустой список — проверка отключена.",
        "help_setting_phrases_expert":
            "Background binding — распространённый артефакт LoRA: когда конкретные текстурные или"
            " локационные токены систематически встречаются в подписях датасета, они вплетаются в embedding"
            " trigger token. Фильтр вынуждает нормализатор заменять overspecific setting descriptions"
            " на coarse location tokens, снижая text-level корреляцию между trigger и конкретным окружением.",
        "help_setting_phrases_tech":
            "Одна фраза на строку. Используется rule_checker для SETTING_OVERSPECIFIC.",
        "help_source_ref_what":
            "В датасете есть два принципиально разных типа изображений: ваши реальные фотографии персонажа —"
            " эталонные снимки, по которым модель учит, как персонаж выглядит «на самом деле» — и"
            " сгенерированные обучающие примеры с разнообразными фонами. Эталонные снимки сделаны в конкретных"
            " условиях: например, в студии на сером фоне. Это поле задаёт фразу, которая обязана присутствовать"
            " в подписи к каждому такому снимку. Если её нет — система выдаст предупреждение: скорее всего,"
            " подпись описывает фон неточно.",
        "help_source_ref_how":
            "Введите одну фразу, которая точно описывает фон на ваших эталонных фотографиях: например,"
            " gray studio background, white seamless background, plain wall. Эта фраза будет проверяться"
            " в каждой подписи к эталонным изображениям. Если снимки сделаны в разных условиях —"
            " выберите одну общую формулировку, которая подходит для всех.",
        "help_source_ref_expert":
            "Эталонные изображения задают reference distribution персонажа — именно по ним модель учит его"
            " истинный облик. Если их подписи содержат те же фоновые токены, что и синтетические изображения,"
            " модель не может разграничить эти два распределения, и качество identity binding снижается."
            " Обязательный токен фона создаёт стабильный caption signature для reference distribution,"
            " изолируя её от synthetic distribution.",
        "help_source_ref_tech":
            "Токен, обязательный в captions source-ref изображений (SOURCE_REF_PATTERN_VIOLATION).",
        "help_coarse_setting_what":
            "В приложении есть ИИ-нормализатор — он автоматически приводит подписи к правильному формату."
            " Этот параметр содержит его конкретную инструкцию о том, как описывать фон и обстановку:"
            " насколько обобщённо, что можно упоминать, а что — нет. По умолчанию инструкция говорит"
            " «называй тип места в 2–4 словах, не упоминай конкретные предметы» — именно это обеспечивает"
            " работу двух предыдущих параметров. Если ваш проект требует другого подхода к описанию"
            " фона — здесь вы можете это изменить.",
        "help_coarse_setting_how":
            "Пишите на английском языке — нормализатор работает с английским. Формулируйте конкретно:"
            " что хотите видеть в описании фона, сколько слов, какие примеры допустимы. Если вас устраивает"
            " стандартное поведение — не меняйте это поле. Изменение влияет на все будущие подписи в проекте,"
            " но не пересчитывает уже готовые.",
        "help_coarse_setting_expert":
            "Текст инжектируется как сегмент в system prompt нормализатора, заменяя стандартную инструкцию"
            " по coarse setting. Для character LoRA дефолт оптимален: coarse location tokens предотвращают"
            " background binding. Для style LoRA или object LoRA логика другая — setting может быть"
            " нерелевантным или ключевым элементом обучения. Это поле позволяет адаптировать поведение"
            " нормализатора под тип проекта без правки исходных промптов.",
        "help_coarse_setting_tech":
            "Инструкция по coarse setting, вставляется в промпт normalizer'а.",
        "help_normalizer_rules_what":
            "ИИ-нормализатор пишет подписи по набору стандартных правил: что описывать, в каком порядке,"
            " каких слов избегать. Но у каждого проекта могут быть свои требования, которых в стандарте нет."
            " Например: «всегда упоминай, есть ли у персонажа головной убор», «никогда не используй слово"
            " casual», «если видно обувь — обязательно опиши её цвет». Этот параметр позволяет добавить"
            " такие правила поверх стандартных — без изменения кода приложения.",
        "help_normalizer_rules_how":
            "Пишите на английском языке. Правила добавляются в конец стандартной инструкции нормализатора,"
            " поэтому они дополняют, а не заменяют его базовое поведение. Оставьте поле пустым, если"
            " дополнительные правила не нужны. Изменения влияют только на будущие подписи —"
            " уже обработанные не пересчитываются.",
        "help_normalizer_rules_expert":
            "Free-text сегмент, инжектируемый в конец system prompt нормализатора. Применяется только"
            " к нормализатору, не к checker'у — для валидационных правил используйте следующий параметр."
            " Удобно для project-specific caption schema extensions: дополнительные обязательные слоты,"
            " vocabulary restrictions, структурные требования, которые не покрывает дефолтная схема.",
        "help_normalizer_rules_tech":
            "Дополнительные правила, добавляемые в конец prompts/normalizer_system.txt (опционально).",
        "help_checker_rules_what":
            "В приложении два ИИ работают последовательно: сначала нормализатор пишет подпись, затем"
            " валидатор проверяет её. Валидатор не переписывает — он только читает готовую подпись и решает,"
            " соответствует ли она требованиям. Если нет — возвращает нормализатору на доработку. Этот"
            " параметр позволяет добавить свои условия проверки. Например: «предупреждай, если в подписи"
            " упоминается реальное географическое название» или «флагуй подписи, в которых явно указан"
            " возраст персонажа».",
        "help_checker_rules_how":
            "Пишите на английском языке. Формулируйте как условия проверки: что должно быть, чего быть"
            " не должно, что считать нарушением. Оставьте поле пустым, если стандартных правил достаточно."
            " Изменения влияют только на будущие подписи — уже обработанные не пересчитываются.",
        "help_checker_rules_expert":
            "Free-text сегмент, инжектируемый в конец system prompt checker'а — отдельно от normalizer"
            " rules. Checker работает как второй LLM-pass после нормализации: выносит вердикт по готовой"
            " подписи, не переписывая её. Правила здесь — это validation criteria, а не writing guidelines."
            " Нарушение инициирует retry normalizer loop с указанием конкретного нарушения.",
        "help_checker_rules_tech":
            "Дополнительные правила, добавляемые в конец prompts/checker_system.txt (опционально).",
    },
    "en": {
        # Nav
        "nav_projects":    "Projects",
        "nav_settings":    "Settings",
        "nav_journal":     "Journal",
        "nav_help":        "Help",
        "help_not_found":  "Section in development",
        "nav_lang_switch": "RU",
        # Batch form tabs
        "tab_overview": "Overview",
        "tab_items":    "Items",
        "tab_review":   "Review",
        # Decision buttons
        "btn_accept":     "Accept",
        "btn_regenerate": "Regenerate",
        "btn_drop":       "Drop",
        "btn_skip":       "Skip",
        # Common buttons / labels
        "btn_save":            "Save",
        "btn_cancel":          "Cancel",
        "btn_refresh":         "Refresh",
        "btn_create":          "Create",
        "btn_delete":          "Delete",
        "lbl_warnings":        "Warnings",
        "lbl_caption":         "Caption",
        "lbl_error":           "Error",
        "lbl_state":           "State",
        "lbl_file":            "File",
        "lbl_decision":        "Decision",
        "lbl_all":             "All",
        "lbl_filter":          "Filter",
        "lbl_no_items":        "No items.",
        "lbl_no_items_filter": "No items matching the current filter.",
        # Projects list
        "page_projects":       "Projects",
        "btn_create_project":  "Create project",
        "lbl_no_projects":     "No projects.",
        # Settings
        "settings_ui_section":  "UI",
        "settings_ui_language": "Interface language",
        # Navigation / breadcrumbs
        "lbl_back":             "← Back",
        "lbl_back_to_list":     "← Back to list",
        "lbl_projects_breadcrumb": "Projects",
        # Batch form — Overview tab
        "lbl_items_by_state":   "Items by state",
        "lbl_no_items_scan":    "No items. Click «Scan» to discover images.",
        "lbl_state_history":    "State history",
        "lbl_state_history_empty": "No history yet",
        "lbl_errors_section":   "Errors",
        "lbl_select_item_review": "Select an item from the list",
        # Batch lifecycle
        "btn_pause":            "Pause",
        "btn_resume":           "Resume",
        "btn_abort":            "Abort",
        "btn_export":           "Export",
        "btn_scan":             "🔍 Scan",
        "btn_reprocess":        "↻ Reprocess",
        "btn_retry_errors":     "↻ Retry errors",
        "btn_edit_schedule":    "Edit schedule",
        "btn_open_review":      "Open review",
        "btn_open":             "Open",
        "lbl_action_done":      "done",
        "lbl_scan_complete":    "Scan complete",
        "lbl_error_generic":    "Error",
        "lbl_saved":            "Saved",
        "lbl_batch_deleted":    "Batch deleted",
        # Batch items tab
        "lbl_selected_count":   "Selected:",
        "lbl_mass_actions":     "Mass actions ▾",
        "lbl_mass_accept":      "Accept selected",
        "lbl_mass_drop":        "Drop selected",
        "lbl_mass_skip":        "Skip selected",
        "lbl_mass_regen":       "Regenerate selected",
        "lbl_include_warnings": "Include items with warnings in Accept",
        "lbl_warn_count":       "warn.",
        "lbl_gen_prompt":       "Generation prompt:",
        "btn_open_in_review":   "Open in Review →",
        # Item detail
        "lbl_caption_not_ready": "Caption not ready",
        "lbl_warnings_detail":  "Warnings",
        "lbl_gen_context":      "Generation context",
        "lbl_candidate_prompts": "Metadata prompts (reference)",
        "lbl_analyst_output":   "Analyst output (VLM)",
        "lbl_select_item":      "Select an item from the list",
        # Batch header
        "lbl_queued_state":     "In queue...",
        "lbl_scanning_state":   "Scanning...",
        "lbl_processing_count": "processing",
        "lbl_errors_count":     "errors",
        "lbl_awaiting_count":   "waiting",
        "lbl_review_short":     "review",
        "lbl_scanning_progress": "Scanning",
        "lbl_schedule_label":   "Schedule:",
        # Batch cards
        "lbl_scheduled_at":     "Scheduled @",
        "lbl_no_batches":       "No batches.",
        "lbl_approved_short":   "approved",
        # Project card
        "lbl_errors_batches":   "errors",
        "lbl_awaiting_review":  "awaiting review",
        "lbl_active_batches":   "active",
        "lbl_no_batches_card":  "no batches",
        # Server summary
        "lbl_total_projects":   "Projects:",
        "lbl_active_batches_sum": "Active batches:",
        "lbl_awaiting_review_sum": "Awaiting review:",
        "lbl_scheduled_sum":    "Scheduled:",
        "lbl_errors_sum":       "Errors:",
        "lbl_queue_depth":      "Queue:",
        # Projects list
        "btn_create_first":     "+ Create first project",
        "lbl_create_project_title": "Create project",
        "lbl_name_field":       "Name *",
        "lbl_description_field": "Description",
        "lbl_desc_placeholder": "Brief description...",
        "lbl_loading_create":   "Creating...",
        "lbl_name_required_err": "Name is required",
        "lbl_create_error":     "Create failed",
        # Project workspace
        "lbl_no_description":   "No description",
        "lbl_type_label":       "Type:",
        "lbl_output_label":     "Output:",
        "lbl_created_label":    "Created:",
        "lbl_name_label":       "Name",
        "lbl_description_label": "Description",
        "btn_edit":             "Edit",
        "lbl_batches_section":  "Batches",
        "btn_project_logs":     "📋 Project logs",
        "btn_create_batch":     "+ Create batch",
        "lbl_trigger_token_hint": "Unique token for this LoRA. Used in all captions.",
        "lbl_lora_type":          "LoRA type",
        "lbl_base_model_family":  "Base model",
        "lbl_base_model_hint":    "E.g. flux, sdxl, sd15, hunyuan",
        "lora_type_character":    "character",
        "lora_type_creature":     "creature",
        "lora_type_style":        "style",
        "lora_type_clothing":     "clothing",
        "lora_type_pose":         "pose",
        "lora_type_object":       "object",
        "lora_type_face":         "face",
        "lbl_create_batch_title": "Create batch",
        "lbl_images_folder":    "Images folder *",
        "lbl_source_type":      "Source type",
        "lbl_branch_label":     "Branch",
        "lbl_schedule_optional": "Schedule (optional)",
        "lbl_browse":           "📁 Browse…",
        "lbl_folder_picker_title": "Select folder",
        "btn_go":               "Go",
        "btn_up":               "⬆ Up",
        "lbl_loading":          "Loading…",
        "lbl_no_subdirs":       "No subdirectories.",
        "lbl_dblclick_hint":    "Double-click to enter folder. Click to select.",
        "btn_select_folder":    "Select this folder",
        "lbl_required_name_folder": "Name and folder are required",
        "lbl_settings_title":   "Settings",
        # Journal
        "page_journal":         "Journal",
        "lbl_level_filter":     "Level",
        "lbl_project_filter":   "Project",
        "lbl_date_from":        "Date from",
        "lbl_date_to":          "Date to",
        "lbl_search_label":     "Search",
        "lbl_search_placeholder": "Text...",
        "btn_apply_filters":    "Apply",
        "btn_reset_filters":    "Reset",
        "btn_delete_filtered":  "🗑 Delete filtered",
        "lbl_journal_time":     "Time",
        "lbl_journal_level":    "Level",
        "lbl_journal_event":    "Event",
        "lbl_journal_message":  "Message",
        "lbl_journal_empty":    "Journal is empty.",
        "lbl_journal_prev":     "← Prev",
        "lbl_journal_next":     "Next →",
        "lbl_journal_page":     "Page",
        "lbl_journal_of":       "of",
        # Settings — section names (sidebar + headings)
        "settings_section_retry":    "Retry & Errors",
        "settings_section_polling":  "Polling (seconds)",
        "settings_section_paths":    "Paths & Storage",
        "settings_section_logging":  "Logging",
        "settings_section_database": "Database",
        # Settings — saved/applied indicators
        "lbl_saved_indicator":  "✓ Saved",
        "lbl_applied_indicator":"✓ Applied",
        "lbl_overrides_cleared": "Overrides cleared",
        "lbl_save_error":        "Save error",
        # Settings — Retry section
        "settings_normalizer_retries":       "Normalizer max self-retries",
        "settings_consecutive_threshold":    "Consecutive failure threshold (batch halt)",
        # Settings — Polling section
        "settings_poll_projects_list":       "Projects list",
        "settings_poll_project_workspace":   "Project workspace",
        "settings_poll_batch_processing":    "Batch processing",
        "settings_poll_batch_idle":          "Batch idle/done",
        # Settings — Logging section
        "settings_log_level":       "Log level",
        "settings_log_retention":   "Business log retention (days)",
        "settings_log_enable":      "Enable",
        # Settings — Paths section
        "settings_bootstrap_hint":   "Bootstrap paths (from env / config.toml, not editable via UI):",
        "settings_host_port":        "server host/port",
        "settings_data_dir":         "data directory",
        # Settings — Database section
        "settings_db_conn_hint":     "Connection string is set via env variable",
        "settings_db_default_hint":  "default: SQLite in data/ folder",
        "settings_db_integrity":     "DB Integrity Check",
        "settings_db_integrity_desc":"Runs FK constraint checks and anomalous state counts.",
        "settings_db_run_check":     "🔍 Run check",
        "settings_db_admin":         "Administration",
        "settings_db_admin_desc":    "Restart applies code or config changes without manual terminal intervention.",
        "settings_db_restart":       "↺ Restart server",
        # Settings — per-step overrides
        "settings_clear_overrides":  "↺ Clear all overrides",
        "lbl_hide":                  "Hide",
        "lbl_show":                  "Show",
        "lbl_reset_to_main":         "Reset to main",
        # Settings — LLM profiles JS
        "lbl_profile_activated":     "Profile activated — page reloading",
        "lbl_activation_error":      "Activation error",
        "lbl_request_error":         "Request error",
        "confirm_delete_profile":    "Delete profile?",
        "lbl_cannot_delete_active":  "Cannot delete active profile — switch first",
        "lbl_delete_error":          "Delete error",
        "lbl_profile_exists":        "Profile with this name already exists",
        "lbl_name_taken":            "This name is already taken",
        "lbl_rename_error":          "Rename error",
        "lbl_profile_not_selected":  "No profile selected",
        # Settings — restart / integrity check JS
        "lbl_sending_request":       "Sending request...",
        "lbl_server_restarting":     "Server restarting. Page will refresh in 4 seconds...",
        "lbl_restart_error_prefix":  "Error: ",
        "lbl_unknown_error":         "unknown error",
        "lbl_connection_error_restart": "Connection error. Server may already be restarting — refresh the page manually.",
        "lbl_checking":              "Checking...",
        # Journal JS
        "confirm_delete_logs":       "Delete {n} records?",
        "lbl_deleted_count":         "Deleted: ",
        # Settings — remaining
        "settings_lbl_profiles":   "LLM Profiles",
        "settings_select_profile": "— select profile —",
        "btn_activate":         "Activate",
        "btn_test_connection":  "🔌 Test",
        "btn_rename":           "Rename",
        "lbl_no_profiles_hint": "No profiles yet — save the current config as the first profile:",
        "btn_save_as_profile":  "+ Save current config as profile…",
        "lbl_new_profile_title": "New profile",
        "lbl_profile_name":     "Name",
        "lbl_profile_desc":     "Description (optional)",
        "lbl_rename_profile_title": "Rename profile",
        "lbl_llm_main_config":  "LLM — main configuration",
        "lbl_llm_per_step":     "Per-step LLM overrides",
        "lbl_check_connection": "🔌 Check connection",
        # Base JS
        "js_server_error":      "Server error: ",
        "js_connection_lost":   "Connection lost",
        # ETA / time display
        "eta_computing":        "computing…",
        "eta_soon":             "soon",
        "lbl_time_min":         "m",
        "lbl_time_sec":         "s",
        # Analysis panel (D-108)
        "lbl_analysis_title":    "Dataset Analysis",
        "lbl_analysis_total":    "Total items:",
        "lbl_analysis_approved": "Approved:",
        "lbl_analysis_awaiting": "Awaiting review:",
        "lbl_analysis_framing":  "Framing",
        "lbl_analysis_view":     "View",
        "lbl_analysis_clothing": "Clothing state",
        "lbl_analysis_source_type": "Source type",
        "lbl_analysis_warnings": "Warnings",
        "lbl_analysis_pose":      "Pose",
        "lbl_analysis_per_batch": "Per batch",
        "lbl_analysis_no_items": "No APPROVED/AWAITING_REVIEW items in this project.",
        "lbl_analysis_recommendations": "Recommendations",
        "lbl_analysis_recs_healthy": "Dataset looks balanced — no recommendations.",
        "lbl_analysis_llm_unavailable": "LLM analysis unavailable — check Settings → LLM or server logs.",
        # Warning code labels
        "warn_TRIGGER_MISSING":              "Trigger token missing",
        "warn_FRAMING_INVALID":              "Invalid framing",
        "warn_VIEW_INVALID":                 "Invalid view",
        "warn_STYLE_TOKEN":                  "Style token",
        "warn_AGE_PHRASE":                   "Age phrase",
        "warn_NEGATIVE_WORDING":             "Negative wording",
        "warn_IDENTITY_OVERCAPTION":         "Identity overcaption",
        "warn_NUDE_ON_CROPPED_PORTRAIT":     "Nude on cropped portrait",
        "warn_SOURCE_REF_PATTERN_VIOLATION": "Source ref pattern violation",
        "warn_ADULT_BRANCH_MISMATCH":        "Adult branch mismatch",
        "warn_MULTI_CHARACTER":              "Multiple characters",
        "warn_SLOT_MISSING":                 "Slot missing",
        "warn_SETTING_OVERSPECIFIC":         "Setting too specific",
        "warn_CLOTHING_OVERDESCRIBED":       "Clothing over-described",
        "warn_GAP_FILLED_FROM_PROMPT":       "Gap filled from prompt (verify)",
        "warn_GAP_UNFILLABLE":               "Gap could not be filled",
        # Caption policy (D-114)
        "lbl_caption_policy":              "Caption Policy",
        "lbl_identity_trait_patterns":     "Identity trait patterns (regex)",
        "lbl_setting_overspecific_phrases":"Forbidden setting phrases",
        "lbl_source_ref_setting":          "Source ref setting token",
        "lbl_coarse_setting_note":         "Coarse setting rule",
        "lbl_custom_normalizer_rules":     "Custom normalizer rules",
        "lbl_custom_checker_rules":        "Custom checker rules",
        "lbl_policy_using_defaults":       "Using project defaults (caption_policy is null)",
        "btn_save_policy":                 "Save policy",
        "btn_reset_policy":                "Reset to defaults",
        "lbl_for_experts": "▸ For advanced users",
        # Caption policy — 4-part help texts
        "help_identity_patterns_what":
            "A list of phrases forbidden in your character's training image captions."
            " Here's an example: suppose every caption says \"gray eyes\"."
            " The model then learns the eye color through text rather than the visual image."
            " In practice, this means: if you don't write \"gray eyes\" in your generation prompt,"
            " the character may get a random eye color — because this feature was never visually embedded."
            " But if you exclude \"gray eyes\" from all captions, the model learns this color only from"
            " the images, and the character will always have gray eyes automatically,"
            " even without mentioning it in the prompt.",
        "help_identity_patterns_how":
            "List all such features of your character to bind them automatically."
            " Enter one expression per line. Plain words work fine: gray eyes, distinctive nose —"
            " the system will find them anywhere in the caption."
            " Regular expressions are supported for flexible matching:"
            " gray eyes(?: clearly visible)? will catch both variants."
            " An empty list disables the check. The longer the list, the stricter the filter.",
        "help_identity_patterns_expert":
            "In a LoRA dataset, appearance descriptions in captions create unwanted text-visual correlation:"
            " if \"gray eyes\" appears in 80% of captions, the model ties this phrase to the trigger token"
            " and reproduces it without an explicit prompt. Identity should be anchored through visual"
            " repetition, not text co-occurrence — otherwise you lose controllability."
            " The app automatically checks each caption and sends it for reformulation,"
            " preventing appearance descriptions from entering the dataset.",
        "help_identity_patterns_tech":
            "One regex pattern per line. Used by rule_checker for IDENTITY_OVERCAPTION.",
        "help_setting_phrases_what":
            "A list of phrases forbidden when describing backgrounds and surroundings."
            " Here's an example: your training images were generated in various locations,"
            " but many feature wooden buildings, logs, and fences."
            " One image gets captioned \"wooden building\", another \"log cabin\", another \"wooden fence\"."
            " Each phrase is different, but together they gradually bind the character to wooden structures."
            " Replace all these specific descriptions with a neutral \"outdoor setting\" —"
            " the character is left without a fixed background, and you can place them anywhere"
            " with a single word in your prompt."
            " In short: replace specific descriptions with broad ones that don't tie the character"
            " to particular surrounding objects.",
        "help_setting_phrases_how":
            "List specific background details that FREQUENTLY appear in your training images:"
            " materials, architectural elements, distinctive objects."
            " Enter one phrase per line — the system will find them anywhere in the caption"
            " and ask the AI to replace the description with a more general one."
            " An empty list disables the check.",
        "help_setting_phrases_expert":
            "Background binding is a common LoRA artifact: when specific texture or location tokens"
            " appear systematically in dataset captions, they become embedded in the trigger token's"
            " representation. The filter forces the normalizer to replace overspecific setting descriptions"
            " with coarse location tokens, reducing text-level correlation between the trigger"
            " and specific surroundings.",
        "help_setting_phrases_tech":
            "One phrase per line. Used by rule_checker for SETTING_OVERSPECIFIC.",
        "help_source_ref_what":
            "Your dataset contains two fundamentally different types of images: your actual reference photos —"
            " the ground-truth shots the model uses to learn what the character really looks like —"
            " and synthetically generated training examples with varied backgrounds."
            " Reference photos were taken in controlled conditions (e.g., a studio with a gray background)."
            " This field sets the phrase that must appear in every reference photo caption."
            " If it's absent, the system will warn you: the caption likely describes the background inaccurately.",
        "help_source_ref_how":
            "Enter a single phrase that accurately describes the background in your reference photos:"
            " for example, gray studio background, white seamless background, plain wall."
            " This phrase will be checked in every reference image caption."
            " If your shots were taken in different conditions,"
            " choose one general formulation that fits all of them.",
        "help_source_ref_expert":
            "Reference images define the character's reference distribution — the model uses them to learn"
            " the character's true appearance. If their captions share background tokens with synthetic"
            " images, the model cannot separate these two distributions, and identity binding quality suffers."
            " The required setting token creates a stable caption signature for the reference distribution,"
            " isolating it from the synthetic training distribution.",
        "help_source_ref_tech":
            "Token required in source-ref image captions (SOURCE_REF_PATTERN_VIOLATION).",
        "help_coarse_setting_what":
            "The app includes an AI normalizer that automatically brings captions into the correct format."
            " This parameter contains its specific instruction about how to describe backgrounds and settings:"
            " how general to be, what words are acceptable, and what to avoid."
            " By default, the instruction says \"name the type of place in 2–4 words, don't mention"
            " specific objects\" — this is what makes the previous two parameters work."
            " If your project requires a different approach to setting descriptions, you can change it here.",
        "help_coarse_setting_how":
            "Write in English — the normalizer works in English."
            " Be specific: what you want to see in background descriptions, how many words,"
            " what examples are acceptable. If you're happy with the default behavior, don't change this field."
            " Changes affect all future captions in the project, but don't reprocess already completed ones.",
        "help_coarse_setting_expert":
            "The text is injected as a segment into the normalizer's system prompt,"
            " replacing the default coarse setting instruction."
            " For character LoRA, the default is optimal: coarse location tokens prevent background binding."
            " For style LoRA or object LoRA, the logic differs — setting may be irrelevant or,"
            " on the contrary, a key learning element."
            " This field allows adapting normalizer behavior to the project type without editing source prompts.",
        "help_coarse_setting_tech":
            "Coarse setting instruction, injected into the normalizer prompt.",
        "help_normalizer_rules_what":
            "The AI normalizer writes captions according to a set of standard rules:"
            " what to describe, in what order, what words to avoid."
            " But every project may have its own requirements not covered by the standard."
            " For example: \"always mention headwear if visible\","
            " \"never use the word casual\","
            " or \"if footwear is visible, always describe its color\"."
            " This parameter lets you add such rules on top of the standard ones —"
            " without modifying any application code.",
        "help_normalizer_rules_how":
            "Write in English. Rules are appended after the standard normalizer instructions,"
            " so they supplement rather than replace its core behavior."
            " Leave the field empty if no additional rules are needed."
            " Changes affect only future captions — already processed ones are not recomputed.",
        "help_normalizer_rules_expert":
            "Free-text segment injected at the end of the normalizer's system prompt."
            " Applied only to the normalizer, not the checker —"
            " use the next field for validation rules."
            " Useful for project-specific caption schema extensions:"
            " additional required slots, vocabulary restrictions,"
            " structural requirements not covered by the default schema.",
        "help_normalizer_rules_tech":
            "Additional rules appended to the end of prompts/normalizer_system.txt (optional).",
        "help_checker_rules_what":
            "The app runs two AI passes in sequence: first the normalizer writes the caption,"
            " then the checker validates it. The checker doesn't rewrite — it only reads the finished"
            " caption and decides whether it meets requirements."
            " If not, it sends it back to the normalizer for revision."
            " This parameter lets you add your own validation conditions."
            " For example: \"warn if a real geographic location is mentioned\""
            " or \"flag captions that explicitly state the character's age\".",
        "help_checker_rules_how":
            "Write in English. Formulate as validation conditions:"
            " what should be present, what shouldn't, what counts as a violation."
            " Leave the field empty if the default rules are sufficient."
            " Changes affect only future captions — already processed ones are not recomputed.",
        "help_checker_rules_expert":
            "Free-text segment injected at the end of the checker's system prompt —"
            " separately from normalizer rules."
            " The checker operates as a second LLM pass after normalization:"
            " it renders a verdict on the finished caption without rewriting it."
            " Rules here are validation criteria, not writing guidelines."
            " A violation triggers a normalizer retry loop with the specific violation flagged.",
        "help_checker_rules_tech":
            "Additional rules appended to the end of prompts/checker_system.txt (optional).",
    },
}


def get_t(lang: str) -> dict[str, str]:
    """Return the translation dict for *lang*. Falls back to 'ru' for unknown values."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
