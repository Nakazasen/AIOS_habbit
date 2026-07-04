@echo off
cd /d "%~dp0"

echo Checking dependencies...
py -3 -m pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo Streamlit not found. Installing dependencies...
    py -3 -m pip install -e .
    if %errorlevel% neq 0 (
        echo Launcher missing package/dependency problem: Khong the cai dat cac goi phu thuoc. Vui long kiem tra lai.
        pause
        exit /b 1
    )
)

echo Starting AIOS Habit Workspace Chat...
set PYTHONPATH=src
py -3 -m streamlit run src\aios_habit\workspace_chat_app.py
pause
