## 2026-08-20T13:39:57Z
Your working directory is: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_auditor_1
Project root: d:\Sandbox\AIOS_habbit
Original requirements file: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
PROJECT.md: C:\Users\Admin\.gemini\antigravity\brain\085caf98-0e6e-4709-bce0-a3cf6358fe59\PROJECT.md

You MUST read d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md before starting work.
Your task is to conduct a rigorous, zero-tolerance Forensic Integrity Audit across all source code, scripts, and tests:
1. Static code forensics:
   - Check `src/aios_habit/mom_local_index.py` for any hardcoded query lists (`q1_terms`, `q2_terms`, `q3_terms`), artificial multipliers, or file penalties (`-50.0`, `erd_kho_van_new.html`).
   - Check `src/aios_habit/excel_extractors.py` for hardcoded 1,000-row or 20,000-cell truncation limits or dummy chunking implementations.
   - Check `scripts/generate_ai_grounded_report.py` and `scripts/run_workspace_chat_12_questions.py` for `POLISHED_ANSWERS`, canned response dictionaries, or fabricated score values.
   - Check `tests/test_mom_search_bm25_zero_hardcode.py` for genuine AST checks and valid assertions (no no-op tests, no trivial `assert True`).
2. Verify that there is zero cheating, zero mock facades, and zero task circumvention.
3. Provide a comprehensive audit report in your working directory (.agents/teamwork_preview_auditor_1/handoff.md) with a clear binary verdict: CLEAN or INTEGRITY VIOLATION. Send a message back with your verdict.
