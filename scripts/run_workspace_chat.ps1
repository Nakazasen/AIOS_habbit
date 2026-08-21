$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$env:PYTHONPATH = "src"

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "Starting AIOS WorkLens Workspace Chat via uv..."
    uv run --no-sync streamlit run src\aios_habit\workspace_chat_app.py
} elseif (Test-Path "$RepoRoot\.venv\Scripts\streamlit.exe") {
    Write-Host "Starting AIOS WorkLens Workspace Chat via .venv streamlit..."
    & "$RepoRoot\.venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py
} elseif (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    Write-Host "Starting AIOS WorkLens Workspace Chat via .venv python..."
    & "$RepoRoot\.venv\Scripts\python.exe" -m streamlit run src\aios_habit\workspace_chat_app.py
} else {
    Write-Host "Starting AIOS WorkLens Workspace Chat via Python 3.12..."
    py -3.12 -m streamlit run src\aios_habit\workspace_chat_app.py
}
