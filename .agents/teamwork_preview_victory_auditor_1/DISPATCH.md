## 2026-08-18T15:07:00Z
You are teamwork_preview_victory_auditor.
Working directory for your metadata (BRIEFING.md, progress.md, handoff.md, audit_report.md, etc.): d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_victory_auditor_1
Target project directory: C:\Users\Admin\teamwork_projects\c_drive_cleanup

<original_task>
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
</original_task>

Conduct an independent post-victory audit:
1. Conduct Phase 1: Timeline & Git/Workspace verification.
2. Conduct Phase 2: Cheating & Hardcoding detection (verify real implementation, no fake mocks, strict Downloads safety, locked file handling, reparse point/junction isolation).
3. Conduct Phase 3: Independent test execution by running `Run-Tests.ps1` and live dry-run checks.
4. Report structured verdict (CONFIRMED / REJECTED) with detailed findings in `audit_report.md` and send a message back.
