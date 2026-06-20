# AIOS Case Cockpit v0.1

The **AIOS Case Cockpit** is a local UI designed for handling specific support or development "cases".

## Features
- **Case Management**: Create, track, and update the status and priority of individual cases.
- **Evidence Ingestion**: Upload Excel/CSV spreadsheets and image screenshots directly to the case. Add logs and chat pastes seamlessly.
- **Visual Case Map**: Generates a local architecture graph of how case evidence and hypotheses connect.
- **Rule-based Next Actions**: Suggests next steps depending on what is missing from the case investigation.
- **AI Prompt Pack**: Safely formats the case situation, logs, and evidence into a copyable prompt for external LLMs (ChatGPT, Gemini, Copilot, NotebookLM), while rigorously preventing the inclusion of `local_only` raw data in cloud prompts.
- **Handover Generation**: Quickly print the case status for team handover.

## Data Storage
All case data and uploaded assets are stored strictly in `local_cases/` at the repository root. This directory is git-ignored and ensures total privacy.

## Launching
- Run `RUN_AIOS_CASE_COCKPIT.bat`
- Or use `.\scripts\run_case_cockpit.ps1`
- Or run `py -3 -m streamlit run src\aios_habit\case_cockpit.py`
