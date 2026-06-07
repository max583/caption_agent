@echo off
setlocal

:: ============================================================
:: Caption Agent — dev launcher (uvicorn hot-reload ON)
:: Python file changes restart the server automatically.
:: Jinja2 templates reload on every request regardless.
:: DB schema changes still require a manual restart + DB recreate.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV=%SCRIPT_DIR%.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: %VENV%
    echo Run setup first:
    echo   cd scripts\caption_agent
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev]"
    pause
    exit /b 1
)

set CAPTION_AGENT_RELOAD=1
set CAPTION_AGENT_LOG_LEVEL=DEBUG

set "HOST=%CAPTION_AGENT_HOST%"
set "PORT=%CAPTION_AGENT_PORT%"
if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8765"

echo.
echo  Caption Agent  [dev: hot-reload ON]
echo  http://%HOST%:%PORT%
echo  Press Ctrl+C to stop.
echo.

"%VENV%\Scripts\python.exe" -m caption_agent.main

endlocal
