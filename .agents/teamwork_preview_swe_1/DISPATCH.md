## 2026-08-18T14:41:17Z

You are the SWE Light Orchestrator (teamwork_preview_swe).

Working directory: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_swe_1
Target project directory: C:\Users\Admin\teamwork_projects\c_drive_cleanup
Original request file: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md

Please execute the single self-contained SWE task as requested by the user:
- Goal: Write a PowerShell script to automatically clean temporary files (%TEMP%, C:\Windows\Temp) and browser caches (Chrome, Edge in AppData) on drive C to free up storage.
- Critical Constraint: Strictly ignore and never touch the Downloads folder (%USERPROFILE%\Downloads).
- Safe Cleanup: Ignore locked/in-use files gracefully (try/catch or -ErrorAction SilentlyContinue) without breaking execution.
- Output: Report total freed space in human-readable format upon completion.
- Integrity mode: development.

Maintain your BRIEFING.md, plan.md, and progress.md in your working directory. Run the SWE Light loop (implementer, test verification, review) and report back when finished.
