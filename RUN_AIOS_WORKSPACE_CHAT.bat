@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ======================================================================
echo  Starting AIOS WorkLens Workspace Chat (CPU-optimized mode)
echo ======================================================================

set PYTHONPATH=src

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [Launcher] Running via uv in project virtual environment...
    uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

if exist ".venv\Scripts\streamlit.exe" (
    echo [Launcher] Running via .venv\Scripts\streamlit.exe...
    ".venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

if exist ".venv\Scripts\python.exe" (
    echo [Launcher] Running via .venv\Scripts\python.exe...
    ".venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

echo [Launcher] Virtual environment not found in .venv. Trying Python 3.12...
py -3.12 -m streamlit run src\aios_habit\workspace_chat_app.py

:launcher_exit
if %errorlevel% neq 0 (
    echo.
    echo [Launcher] Workspace Chat exited with error code %errorlevel%.
    pause
)
