@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ======================================================================
echo  Dang khoi dong AIOS WorkLens Workspace Chat
echo ======================================================================

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

where uv >nul 2>&1
if not errorlevel 1 goto :run_uv

if exist ".venv\Scripts\streamlit.exe" goto :run_venv_streamlit

if exist ".venv\Scripts\python.exe" goto :run_venv_python

echo [Loi] Khong tim thay moi truong Python hop le. Hay chay 'uv sync' de chuan bi.
pause
exit /b 1

:run_uv
echo [Trinh khoi chay] Dang khoi dong qua uv...
uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:run_venv_streamlit
echo [Trinh khoi chay] Dang khoi dong qua .venv...
".venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:run_venv_python
echo [Trinh khoi chay] Dang khoi dong qua python .venv...
".venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:launcher_exit
if errorlevel 1 (
    echo.
    echo [Trinh khoi chay] Ung dung da dung voi ma trang thai %errorlevel%.
    pause
)
