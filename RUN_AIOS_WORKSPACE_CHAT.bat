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
rem Lan mo dau tien tung cham vi preflight "import torch, FlagEmbedding"
rem nap DLL native roi thoat, sau do moi mo Streamlit. Chi can biet goi da
rem cai. Sidecar cung khong duoc chan cua so nay: app van ket noi khi san sang.
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
set STREAMLIT_SERVER_RUN_ON_SAVE=false

if exist ".venv\Scripts\python.exe" goto :run_venv

where uv >nul 2>&1
if not errorlevel 1 goto :run_uv

echo [Loi] Khong tim thay moi truong Python hop le. Hay chay 'uv sync --inexact' de chuan bi.
pause
exit /b 1

:run_venv
call :ensure_rag ".venv\Scripts\python.exe"
if errorlevel 1 goto :rag_fail
call :start_bridge ".venv\Scripts\python.exe"
echo [Trinh khoi chay] Dang mo Workspace Chat...
if exist ".venv\Scripts\streamlit.exe" (
    ".venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
) else (
    ".venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
)
goto :launcher_exit

:run_uv
call :ensure_rag_uv
if errorlevel 1 goto :rag_fail
call :start_bridge_uv
echo [Trinh khoi chay] Dang mo Workspace Chat...
uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
goto :launcher_exit

:ensure_rag
"%~1" -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('torch','FlagEmbedding')) else 1)" >nul 2>&1
if not errorlevel 1 exit /b 0
echo [Bao ve RAG] Phat hien thieu thu vien FlagEmbedding hoac torch. Dang tu dong khoi phuc...
uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
if errorlevel 1 exit /b 1
"%~1" -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('torch','FlagEmbedding')) else 1)" >nul 2>&1
exit /b %errorlevel%

:ensure_rag_uv
uv run --no-sync python -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('torch','FlagEmbedding')) else 1)" >nul 2>&1
if not errorlevel 1 exit /b 0
echo [Bao ve RAG] Phat hien thieu thu vien FlagEmbedding hoac torch. Dang tu dong khoi phuc...
uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
if errorlevel 1 exit /b 1
uv run --no-sync python -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('torch','FlagEmbedding')) else 1)" >nul 2>&1
exit /b %errorlevel%

:start_bridge
"%~1" -c "import subprocess,sys; subprocess.Popen([sys.executable,'-c','from aios_habit.antigravity_bridge import ensure_antigravity_bridge_running; ensure_antigravity_bridge_running()'], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)" >nul 2>&1
exit /b 0

:start_bridge_uv
uv run --no-sync python -c "import subprocess,sys; subprocess.Popen([sys.executable,'-c','from aios_habit.antigravity_bridge import ensure_antigravity_bridge_running; ensure_antigravity_bridge_running()'], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)" >nul 2>&1
exit /b 0

:rag_fail
echo [Loi] Khong the chuan bi thu vien RAG. Hay chay 'uv sync --inexact' roi mo lai.
pause
exit /b 1

:launcher_exit
if errorlevel 1 (
    echo.
    echo [Trinh khoi chay] Ung dung da dung voi ma trang thai %errorlevel%.
    pause
)
