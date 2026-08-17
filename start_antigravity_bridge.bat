@echo off
echo Starting Antigravity IDE Sidecar Bridge...
echo.
cd /d "%~dp0"
python scripts\antigravity_sidecar_daemon.py
pause
