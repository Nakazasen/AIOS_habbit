## 2026-08-18T23:22:53Z

You are teamwork_preview_auditor_1 (Forensic Integrity Auditor).
Working directory: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_auditor_1
Project root: d:\Sandbox\AIOS_habbit
Original request file: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Project specification: d:\Sandbox\AIOS_habbit\PROJECT.md
Target file to audit: d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json

Task:
Conduct forensic integrity audit on the Vietnamese localization of `knowledge-graph.json`:
1. Static analysis & authentic content check: Verify that every node summary, layer description, and tour description is an authentic, genuine translation of the original content, with zero dummy/mock strings, zero hardcoded cheat patterns, and zero placeholder text.
2. Byte-level integrity check: Verify file encoding (UTF-8), non-corruption of diacritics, and valid JSON structure.
3. Scope conformance: Verify that only the specified file `d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json` and agent metadata were touched, and no unauthorized repository source files were damaged.
4. Output your audit findings to `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_auditor_1\audit_report.md`.
5. Write `handoff.md` with explicit Verdict: CLEAN or INTEGRITY VIOLATION.

Send a completion message back to parent when done.
