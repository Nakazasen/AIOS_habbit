@echo off
cd /d "%~dp0"

echo Checking dependencies for Case Cockpit...
py -3 -m pip show streamlit pandas openpyxl >nul 2>&1
if %errorlevel% neq 0 (
    echo Dependencies missing. Installing...
    py -3 -m pip install -e .
)

echo Starting AIOS Case Cockpit...
set PYTHONPATH=src
py -3 -m streamlit run src\aios_habit\case_cockpit.py
pause
