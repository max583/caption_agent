"""Help documentation renderer (Phase 10A).

Reads Markdown files from docs/help/{lang}/{slug}.md and renders them to
HTML fragments for the /help section of the UI.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown as _md

# ---------------------------------------------------------------------------
# Path to the docs/help/ directory (relative to this file's package location).
# File layout: scripts/caption_agent/caption_agent/services/help_renderer.py
# docs/help is at:  scripts/caption_agent/docs/help/
# ---------------------------------------------------------------------------
_HELP_DIR = Path(__file__).parent.parent.parent / "docs" / "help"

# ---------------------------------------------------------------------------
# Markdown renderer — shared instance with extensions.
# ---------------------------------------------------------------------------
_RENDERER = _md.Markdown(
    extensions=["fenced_code", "tables", "nl2br"],
    output_format="html",
)

# ---------------------------------------------------------------------------
# Navigation tree — 7 sections, 29 pages.
# ---------------------------------------------------------------------------
NAV_TREE: list[dict] = [
    {
        "id": "getting_started",
        "title_ru": "Начало работы",
        "title_en": "Getting Started",
        "pages": [
            {"slug": "what_is",      "title_ru": "Что такое Caption Agent", "title_en": "What is Caption Agent"},
            {"slug": "requirements", "title_ru": "Требования к окружению",  "title_en": "System Requirements"},
            {"slug": "launch",       "title_ru": "Установка и запуск",      "title_en": "Installation & Launch"},
        ],
    },
    {
        "id": "interface",
        "title_ru": "Интерфейс",
        "title_en": "User Interface",
        "pages": [
            {"slug": "ui_overview",  "title_ru": "Обзор интерфейса",           "title_en": "UI Overview"},
            {"slug": "ui_projects",  "title_ru": "Страница «Проекты»",         "title_en": "Projects Page"},
            {"slug": "ui_batch",     "title_ru": "Рабочее пространство батча", "title_en": "Batch Workspace"},
            {"slug": "ui_settings",  "title_ru": "Настройки",                  "title_en": "Settings"},
            {"slug": "ui_journal",   "title_ru": "Журнал",                     "title_en": "Journal"},
        ],
    },
    {
        "id": "concepts",
        "title_ru": "Основные концепции",
        "title_en": "Core Concepts",
        "pages": [
            {"slug": "concepts_lora",       "title_ru": "Что такое LoRA и зачем нужны подписи", "title_en": "What is LoRA and Why Captions Matter"},
            {"slug": "concepts_lora_types", "title_ru": "Типы LoRA",      "title_en": "LoRA Types"},
            {"slug": "concepts_trigger",    "title_ru": "Trigger token",  "title_en": "Trigger Token"},
            {"slug": "concepts_policy",     "title_ru": "Caption policy", "title_en": "Caption Policy"},
        ],
    },
    {
        "id": "pipeline",
        "title_ru": "Пайплайн",
        "title_en": "Pipeline",
        "pages": [
            {"slug": "pipeline_overview",        "title_ru": "Архитектура и компоненты",   "title_en": "Architecture & Components"},
            {"slug": "pipeline_batch_lifecycle", "title_ru": "Жизненный цикл батча",       "title_en": "Batch Lifecycle"},
            {"slug": "pipeline_image_lifecycle", "title_ru": "Жизненный цикл изображения", "title_en": "Image Lifecycle"},
            {"slug": "pipeline_analyst",         "title_ru": "Шаг 1: Анализ",              "title_en": "Step 1: Analyst"},
            {"slug": "pipeline_analyst_schemas",    "title_ru": "Схемы аналитика по типам LoRA",  "title_en": "Analyst Schemas by LoRA Type"},
            {"slug": "pipeline_normalizer",        "title_ru": "Шаг 2: Нормализация",            "title_en": "Step 2: Normalizer"},
            {"slug": "pipeline_normalizer_formats","title_ru": "Форматы подписей по типам LoRA", "title_en": "Caption Formats by LoRA Type"},
            {"slug": "pipeline_rule_checker",    "title_ru": "Шаг 3: Быстрая проверка",    "title_en": "Step 3: Rule Checker"},
            {"slug": "pipeline_llm_checker",     "title_ru": "Шаг 4: Интеллект. проверка", "title_en": "Step 4: LLM Checker"},
            {"slug": "pipeline_export",          "title_ru": "Экспорт",                    "title_en": "Export"},
        ],
    },
    {
        "id": "analytics",
        "title_ru": "Аналитика",
        "title_en": "Analytics",
        "pages": [
            {"slug": "analytics_overview", "title_ru": "Анализ датасета",         "title_en": "Dataset Analysis"},
            {"slug": "analytics_reading",  "title_ru": "Как читать рекомендации", "title_en": "Reading Recommendations"},
        ],
    },
    {
        "id": "reference",
        "title_ru": "Справочник",
        "title_en": "Reference",
        "pages": [
            {"slug": "ref_project_params", "title_ru": "Параметры проекта",        "title_en": "Project Parameters"},
            {"slug": "ref_policy_params",  "title_ru": "Параметры caption policy", "title_en": "Caption Policy Parameters"},
            {"slug": "ref_llm_settings",   "title_ru": "Настройки LLM",            "title_en": "LLM Settings"},
        ],
    },
    {
        "id": "faq",
        "title_ru": "Частые вопросы",
        "title_en": "FAQ",
        "pages": [
            {"slug": "faq_no_trigger",   "title_ru": "Почему caption начинается не с trigger token?",         "title_en": "Why doesn't the caption start with the trigger token?"},
            {"slug": "faq_llm_offline",  "title_ru": "Что делать если LLM не отвечает?",                     "title_en": "What to do if the LLM is not responding?"},
            {"slug": "faq_checkers",     "title_ru": "Чем быстрая проверка отличается от интеллектуальной?", "title_en": "What's the difference between rule checker and LLM checker?"},
            {"slug": "faq_custom_rules", "title_ru": "Как добавить свои правила?",                           "title_en": "How to add custom rules?"},
        ],
    },
]

# Flat slug → page dict for fast lookup.
_SLUG_INDEX: dict[str, dict] = {
    page["slug"]: page
    for section in NAV_TREE
    for page in section["pages"]
}

# Slug → parent section id.
_SLUG_SECTION: dict[str, str] = {
    page["slug"]: section["id"]
    for section in NAV_TREE
    for page in section["pages"]
}

_FIRST_SLUG: str = NAV_TREE[0]["pages"][0]["slug"]


def get_first_slug() -> str:
    """Return the slug of the first help page (redirect target for /help)."""
    return _FIRST_SLUG


def get_page_title(slug: str, lang: str) -> str:
    """Return the page title for the given slug and language."""
    page = _SLUG_INDEX.get(slug)
    if page is None:
        return slug
    key = "title_ru" if lang == "ru" else "title_en"
    return page.get(key, slug)  # type: ignore[return-value]


def get_active_section_id(slug: str) -> str:
    """Return the section id that contains the given slug."""
    return _SLUG_SECTION.get(slug, NAV_TREE[0]["id"])


def render_page(slug: str, lang: str) -> str:
    """Read docs/help/{lang}/{slug}.md and return an HTML fragment.

    Falls back to _placeholder.md if the page file is missing.
    Returns a built-in fallback string if placeholder is also absent.
    """
    lang_dir = _HELP_DIR / lang
    page_path = lang_dir / f"{slug}.md"

    if page_path.exists():
        md_text = page_path.read_text(encoding="utf-8")
    else:
        placeholder = lang_dir / "_placeholder.md"
        if placeholder.exists():
            md_text = placeholder.read_text(encoding="utf-8")
        else:
            # Hard-coded fallback — no files at all (e.g. fresh install).
            md_text = (
                "# Раздел в разработке\n\nЭта страница ещё не написана."
                if lang == "ru"
                else "# Section in Development\n\nThis page has not been written yet."
            )

    # Reset renderer state between calls (markdown lib is stateful).
    _RENDERER.reset()
    html = _RENDERER.convert(md_text)

    # Convert fenced mermaid code blocks to Mermaid.js div elements.
    # The markdown lib renders ```mermaid as <code class="language-mermaid">.
    html = _mermaid_replace(html)

    # Rewrite cross-page links: href="slug.md" → href="/help/slug"
    # so internal links work regardless of where the fragment is loaded.
    html = _rewrite_md_links(html)

    return f'<article class="help-prose">\n{html}\n</article>'


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MERMAID_PATTERN = re.compile(
    r'<pre><code class="language-mermaid">(.*?)</code></pre>',
    re.DOTALL,
)

# Matches href="anything.md" produced by the Markdown renderer for internal links.
_MD_LINK_PATTERN = re.compile(r'href="([^"#][^"]*?)\.md"')


def _mermaid_replace(html: str) -> str:
    """Replace rendered mermaid code blocks with <div class="mermaid">."""
    return _MERMAID_PATTERN.sub(
        lambda m: f'<div class="mermaid">{m.group(1)}</div>',
        html,
    )


def _rewrite_md_links(html: str) -> str:
    """Rewrite href="slug.md" to href="/help/slug" for internal cross-page links."""
    return _MD_LINK_PATTERN.sub(lambda m: f'href="/help/{m.group(1)}"', html)
