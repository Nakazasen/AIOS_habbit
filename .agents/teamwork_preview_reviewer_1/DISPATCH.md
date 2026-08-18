## 2026-08-18T23:23:00Z
You are teamwork_preview_reviewer_1 (Linguistic Quality & Phrasing Reviewer).
Working directory: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_reviewer_1
Project root: d:\Sandbox\AIOS_habbit
Original request file: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Project specification: d:\Sandbox\AIOS_habbit\PROJECT.md
Target file to review: d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json

Task:
1. Conduct an in-depth linguistic review of all Vietnamese translations in `knowledge-graph.json`:
   - Check `project.description`
   - Check all 8 `layers` (`name` and `description`)
   - Check all 9 `tour` steps (`title` and `description`)
   - Check all 142 `nodes` (`summary` field)
2. Verify grammar, tone, clarity, and natural phrasing in Vietnamese.
3. Verify that there are no remaining untranslated English placeholder sentences, awkward literal machine translations, or mojibake/corrupted characters.
4. Output your detailed review findings to `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_reviewer_1\review_report.md`.
5. Write `handoff.md` with explicit Verdict: APPROVE or REQUEST_CHANGES.

Send a completion message back to parent when done.
