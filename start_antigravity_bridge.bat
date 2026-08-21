@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo Starting Antigravity IDE Sidecar Bridge...
echo.

set PYTHONPATH=src

where uv >nul 2>&1
if %errorlevel% equ 0 (
    uv run --no-sync python scripts\antigravity_sidecar_daemon.py
    goto :bridge_exit
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\antigravity_sidecar_daemon.py
    goto :bridge_exit
)

python scripts\antigravity_sidecar_daemon.py

:bridge_exit
if %errorlevel% neq 0 (
    echo [Launcher] Antigravity Sidecar Bridge exited with code %errorlevel%.
    pause
)

