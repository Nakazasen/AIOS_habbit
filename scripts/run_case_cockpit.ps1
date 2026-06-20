$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

if (-not (Get-Command "streamlit" -ErrorAction SilentlyContinue)) {
    Write-Host "Dependencies missing. Installing..."
    py -3 -m pip install -e .
}

Write-Host "Starting AIOS Case Cockpit..."
py -3 -m streamlit run src\aios_habit\case_cockpit.py
