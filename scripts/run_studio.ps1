$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

# Check if streamlit is available
if (-not (Get-Command "streamlit" -ErrorAction SilentlyContinue)) {
    Write-Host "Streamlit not found. Attempting to install dependencies..."
    py -3 -m pip install -e .
}

Write-Host "Starting AIOS Habit Studio..."
$env:PYTHONPATH = "src"
py -3 -m streamlit run src\aios_habit\studio.py
