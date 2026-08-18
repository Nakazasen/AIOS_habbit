# BRIEFING — teamwork_preview_implementer_1

## Task Information
- **Role**: implementer@swe_light
- **Agent ID**: ac49c8c6-4ea0-41a4-a0a3-01458b4c3b4a
- **Parent ID**: 805fddab-1a0c-4777-8f12-617faad22aee
- **Target Project Directory**: C:\Users\Admin\teamwork_projects\c_drive_cleanup
- **Working Directory**: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_implementer_1

## Mission & Requirements
1. Implement a PowerShell cleanup script on drive C:
   - Clean temporary files: `%TEMP%`, `C:\Windows\Temp`
   - Clean browser caches: Chrome, Edge in `AppData` (`Default\Cache`, `Code Cache`, `GPUCache`, etc., across profiles)
2. Critical Safety Constraint:
   - Strictly ignore and never touch the Downloads folder (`%USERPROFILE%\Downloads`).
   - Hardcoded and configurable guardrail protection against Downloads and other system-critical paths.
3. Safe Cleanup:
   - Handle locked / in-use files gracefully (try/catch or `-ErrorAction SilentlyContinue`) without breaking execution.
   - Track skipped/locked files vs deleted files.
4. Human-Readable Reporting:
   - Calculate freed space in bytes and convert to human-readable format (B, KB, MB, GB, TB).
   - Display a detailed summary and return a structured result object.
5. Automated Tests:
   - Write comprehensive unit and integration tests covering:
     - Temp cleanup
     - Browser cache cleanup (Chrome, Edge)
     - Downloads safety exclusion check
     - Locked file graceful recovery
     - Space reporting accuracy
     - `-WhatIf` / `-DryRun` support
     - Custom targets support
6. Handoff:
   - Provide handoff.md with verification record, diff, and test evidence.
