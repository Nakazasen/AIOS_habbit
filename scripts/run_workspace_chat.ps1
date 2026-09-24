$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$env:PYTHONPATH = "src"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"

# Không import torch/FlagEmbedding chỉ để biết gói đã cài. Import đó nạp DLL
# native rồi bỏ tiến trình, nên lần mở đầu (cache lạnh) đứng rất lâu.
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE = "none"
$env:STREAMLIT_SERVER_RUN_ON_SAVE = "false"
$py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$checkBge = & $py -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('torch','FlagEmbedding')) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Bảo vệ RAG] Phát hiện thiếu thư viện FlagEmbedding hoặc torch. Đang tự động khôi phục..."
    & uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" "FlagEmbedding==1.3.5" "transformers==4.44.2" "sentence-transformers==3.1.1"
}

if (Test-Path "$RepoRoot\.venv\Scripts\streamlit.exe") {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat..."
    & "$RepoRoot\.venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
}
elseif (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat..."
    & "$RepoRoot\.venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
}
elseif (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "Đang khởi chạy AIOS WorkLens Workspace Chat..."
    uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false
}
else {
    Write-Host "Không tìm thấy môi trường Python 3.11 được hỗ trợ. Hãy chạy 'uv sync --inexact' trước khi khởi chạy."
}
