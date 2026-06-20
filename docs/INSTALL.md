# Install
Use Python 3.11+.

## AIOS Habit Studio (Web UI)
The recommended way for normal users to interact with AIOS Habit is the Studio UI.
Just double-click `RUN_AIOS_HABIT_STUDIO.bat` at the repository root. It will automatically install `streamlit` if missing and launch the UI.

Alternatively, via PowerShell:
```powershell
.\scripts\run_studio.ps1
```

## CLI Interface (For Agents / Developers)
```powershell
py -3 -m pip install -e .
aios-habit --help
```
No cloud service is required.
