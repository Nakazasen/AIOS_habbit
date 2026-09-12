@echo off
cd /d "%~dp0\.."
echo ========================================================
echo  SMOKE 007 - Thanh nhap chat hien dai (Playwright)
echo  Chrome se mo. Khong gia PASS.
echo ========================================================
uv run --with playwright --no-sync python scripts/smoke_007_modern_chat_composer.py --headed
echo EXIT:%ERRORLEVEL%
pause
