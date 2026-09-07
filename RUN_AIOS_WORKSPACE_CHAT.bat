@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ======================================================================
echo  Đang khởi động AIOS WorkLens Workspace Chat (chế độ tối ưu CPU)
echo ======================================================================

set PYTHONPATH=src
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [Trình khởi chạy] Đang chạy qua công cụ uv trong môi trường dự án...
    uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

if exist ".venv\Scripts\streamlit.exe" (
    echo [Trình khởi chạy] Đang chạy qua môi trường ảo .venv...
    ".venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

if exist ".venv\Scripts\python.exe" (
    echo [Trình khởi chạy] Đang chạy qua môi trường ảo .venv python...
    ".venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
    goto :launcher_exit
)

echo [Lỗi] Không tìm thấy môi trường Python 3.11 hợp lệ. Hãy chạy 'uv sync' để chuẩn bị môi trường.

:launcher_exit
if %errorlevel% neq 0 (
    echo.
    echo [Trình khởi chạy] Ứng dụng đã dừng với mã trạng thái %errorlevel%.
    pause
)
