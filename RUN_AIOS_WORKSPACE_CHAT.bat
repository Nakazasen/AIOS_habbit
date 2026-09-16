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

echo [Loi] Khong tim thay moi truong Python hop le. Hay chay 'uv sync --inexact' de chuan bi.
pause
exit /b 1

:run_uv
rem Kiem tra moi truong RAG BGE-M3 (tu dong phuc hoi neu tung bi uv sync don dep)
uv run --no-sync python -c "import torch, FlagEmbedding" >nul 2>&1
if errorlevel 1 (
    echo [Bao ve RAG] Phat hien thieu thu vien FlagEmbedding hoac torch. Dang tu dong khoi phuc...
    uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
)
echo [Trinh khoi chay] Kiem tra va khoi dong Antigravity Bridge trong nen...
uv run --no-sync python -c "from aios_habit.antigravity_bridge import ensure_antigravity_bridge_running; res = ensure_antigravity_bridge_running(); print('[Bridge] San sang.' if res.ok else '[Bridge] Chua the khoi dong: ' + str(res.reason))"
echo [Trinh khoi chay] Dang khoi dong qua uv...
uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:run_venv_streamlit
rem Kiem tra moi truong RAG BGE-M3 trong .venv
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import torch, FlagEmbedding" >nul 2>&1
    if errorlevel 1 (
        echo [Bao ve RAG] Phat hien thieu thu vien FlagEmbedding hoac torch. Dang tu dong khoi phuc...
        uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
    )
    echo [Trinh khoi chay] Kiem tra va khoi dong Antigravity Bridge trong nen...
    ".venv\Scripts\python.exe" -c "from aios_habit.antigravity_bridge import ensure_antigravity_bridge_running; res = ensure_antigravity_bridge_running(); print('[Bridge] San sang.' if res.ok else '[Bridge] Chua the khoi dong: ' + str(res.reason))"
)
echo [Trinh khoi chay] Dang khoi dong qua .venv...
".venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:run_venv_python
rem Kiem tra moi truong RAG BGE-M3 trong .venv
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import torch, FlagEmbedding" >nul 2>&1
    if errorlevel 1 (
        echo [Bao ve RAG] Phat hien thieu thu vien FlagEmbedding hoac torch. Dang tu dong khoi phuc...
        uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
    )
    echo [Trinh khoi chay] Kiem tra va khoi dong Antigravity Bridge trong nen...
    ".venv\Scripts\python.exe" -c "from aios_habit.antigravity_bridge import ensure_antigravity_bridge_running; res = ensure_antigravity_bridge_running(); print('[Bridge] San sang.' if res.ok else '[Bridge] Chua the khoi dong: ' + str(res.reason))"
)
echo [Trinh khoi chay] Dang khoi dong qua python .venv...
".venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
goto :launcher_exit

:launcher_exit
if errorlevel 1 (
    echo.
    echo [Trinh khoi chay] Ung dung da dung voi ma trang thai %errorlevel%.
    pause
)
