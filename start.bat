@echo on
setlocal

:: ============================================================
:: Caption Agent — launch script
:: Run from any directory; paths are resolved relative to this file.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV=%SCRIPT_DIR%.venv"
set CAPTION_AGENT_RELOAD=1

:: Check venv exists
if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: %VENV%
    echo Run setup first:
    echo   cd scripts\caption_agent
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev]"
    pause
    exit /b 1
)

:: Optional overrides — uncomment and set if needed
:: set CAPTION_AGENT_HOST=127.0.0.1
:: set CAPTION_AGENT_PORT=8765
:: set CAPTION_AGENT_DB_URL=sqlite:///./data/agent.db
:: set CAPTION_AGENT_LLM_API_KEY=your_key_here
:: set CAPTION_AGENT_LOG_LEVEL=INFO
:: set CAPTION_AGENT_RELOAD=1     :: dev hot-reload (or use start-dev.bat)

:: Show effective address
set "HOST=%CAPTION_AGENT_HOST%"
set "PORT=%CAPTION_AGENT_PORT%"
if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8765"

echo.
echo  Caption Agent
echo  http://%HOST%:%PORT%
echo  Press Ctrl+C to stop.
echo.

:: Run
"%VENV%\Scripts\python.exe" -m caption_agent.main

endlocal
