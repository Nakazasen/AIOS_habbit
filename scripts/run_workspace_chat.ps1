$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$env:PYTHONPATH = "src"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat qua uv..."
    uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
}
elseif (Test-Path "$RepoRoot\.venv\Scripts\streamlit.exe") {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat qua .venv..."
    & "$RepoRoot\.venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
}
elseif (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat qua python môi trường ảo..."
    & "$RepoRoot\.venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
}
else {
    Write-Host "Không tìm thấy môi trường Python 3.11 được hỗ trợ. Hãy chạy 'uv sync' trước khi khởi chạy."
}
