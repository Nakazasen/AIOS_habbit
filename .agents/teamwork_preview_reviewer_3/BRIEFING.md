# BRIEFING — teamwork_preview_reviewer (Round 3)

## 1. Task Definition & Requirements
- **Goal:** Write a PowerShell script to automatically clean temporary files (`%TEMP%`, `C:\Windows\Temp`) and browser caches (Google Chrome, Microsoft Edge in AppData) on drive C to free up storage.
- **Critical Constraint:** Strictly ignore and never touch the Downloads folder (`%USERPROFILE%\Downloads`, `C:\Users\*\Downloads`, registry user shell redirects, and short name aliases).
- **Safe Cleanup:** Ignore locked/in-use files gracefully (`try/catch` or `-ErrorAction SilentlyContinue`) without breaking execution.
- **Output:** Report total freed space in human-readable format upon completion (`B`, `KB`, `MB`, `GB`, `TB`, `PB`, `EB`).
- **Integrity Mode:** development.

## 2. Reviewer Focus (Round 3)
1. Re-derive requirements independently and review previous diffs and edge cases.
2. Adversarial attack on target path deduplication (multiple identical paths, pipeline objects with bound parameters).
3. Test suite expansion for edge cases: non-ASCII / Unicode paths, custom exclude paths, simulation combos (`-WhatIf` + `-Quiet` + `-PassThru`).
4. Real-environment validation with Pester test runner and live WhatIf execution against system C: drive.
5. Close remaining ledger items and generate complete verification documentation.
