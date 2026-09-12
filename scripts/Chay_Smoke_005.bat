@echo off
cd /d "%~dp0\.."
echo ========================================================
echo  SMOKE 005 - Chuan bi nguon tang dan (Playwright)
echo  Chrome se mo. Khong gia PASS.
echo ========================================================
uv run --with playwright --no-sync python scripts/smoke_005_incremental_source_prep.py --headed
echo EXIT:%ERRORLEVEL%
pause
