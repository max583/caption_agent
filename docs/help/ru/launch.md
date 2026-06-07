# Установка и запуск

Как установить Caption Agent и запустить его впервые.

## Для начинающих

### Установка

Все команды выполняются в терминале (PowerShell на Windows, Terminal на macOS/Linux).

1. Перейдите в папку `scripts/caption_agent` внутри репозитория:

```
cd scripts\caption_agent
```

2. Создайте виртуальное окружение Python:

```
python -m venv .venv
```

3. Установите приложение и все зависимости:

```
.venv\Scripts\pip install -e ".[dev]"
```

4. Инициализируйте базу данных:

```
.venv\Scripts\alembic upgrade head
```

### Запуск

**На Windows** — проще всего двойным кликом по `start.bat` в папке `scripts/caption_agent`.

Или из терминала:

```
.venv\Scripts\python -m caption_agent.main
```

После запуска откройте браузер и перейдите по адресу: **http://127.0.0.1:8765**

Чтобы остановить сервер — нажмите `Ctrl+C` в терминале.

## Для опытных пользователей

**Установка в editable-режиме** (`-e`) позволяет редактировать код без переустановки пакета. В dev-режиме uvicorn перезапускает сервер при изменении Python-файлов автоматически.

**Dev-запуск** (горячая перезагрузка):

```
start-dev.bat          # Windows
# или:
CAPTION_AGENT_RELOAD=1 CAPTION_AGENT_LOG_LEVEL=DEBUG .venv/bin/python -m caption_agent.main
```

**Переменные окружения для конфигурации:**

| Переменная | По умолчанию | Описание |
|---|---|---|
| `CAPTION_AGENT_HOST` | `127.0.0.1` | Адрес сервера |
| `CAPTION_AGENT_PORT` | `8765` | Порт сервера |
| `CAPTION_AGENT_DB_URL` | `sqlite:///./data/agent.db` | URL базы данных |
| `CAPTION_AGENT_LOG_LEVEL` | `INFO` | Уровень логирования |
| `CAPTION_AGENT_RELOAD` | `0` | `1` — включить hot-reload |
| `CAPTION_AGENT_LLM_API_KEY` | — | Ключ API для всех LLM-шагов |

**Примечание по миграциям:** изменения схемы БД требуют повторного запуска `alembic upgrade head`. При hot-reload это нужно делать вручную.

## После запуска

При первом открытии браузера вы попадёте на страницу «Проекты» — она будет пустой. Следующий шаг — создать первый проект и настроить LLM в разделе «Настройки».

Подробнее об интерфейсе — в разделе [Обзор интерфейса](ui_overview.md).
