$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

if (-not (Get-Command "streamlit" -ErrorAction SilentlyContinue)) {
    Write-Host "Streamlit not found. Installing local dependencies..."
    py -3 -m pip install -e .
}

Write-Host "Starting AIOS WorkLens Workspace Chat..."
$env:PYTHONPATH = "src"
py -3 -m streamlit run src\aios_habit\workspace_chat_app.py
