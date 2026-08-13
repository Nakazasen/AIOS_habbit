# Spec: Excel Structured Query Audit 3 Remediation

## Objective
Remediate the remaining correctness and coverage findings from Audit 3 without expanding the structured-query surface.

## Requirements

### 1. Bounded all-sheets intent
- `plan_excel_query()` MUST recognize all-sheets intent only when `all` is a standalone canonical token or canonical phrase `tat ca` is present.
- It MUST NOT treat substrings in unrelated words (for example `smallest`) as all-sheets intent.
- Ambiguous same-schema workbooks without a valid all-sheets intent or explicit sheet reference MUST continue to fail soft with `ambiguous_sheet_table`.

### 2. Lossless cross-sheet provenance
- Internal aggregate provenance encoding MUST NOT use a delimiter which is legal in an Excel sheet name.
- A sheet named `East,West` MUST round-trip as one provenance record, not two invented sheets.
- A multi-sheet aggregate MUST still return one `StructuredProvenance` per contributing sheet or region.

### 3. Workspace Chat integration coverage
- An integration test must exercise the managed-workbook route through `retrieve_workspace_chat_evidence()` with two sheets.
- It MUST assert evidence header and citation `location_info` list the actual contributing sheets.

### 4. Quality and hygiene
- Remove newly-added blank lines at EOF in affected test files.
- Preserve SQL allow-list, bounded execution limits, and fail-soft behavior.

## Acceptance Criteria
- `smallest Revenue` never selects all sheets merely because it contains `all`.
- A `East,West` sheet name is retained verbatim in aggregate provenance.
- Multi-sheet Workspace Chat evidence cites `Sheets: East, West` for normal two-sheet names.
- Targeted affected suite passes, `py_compile` passes, `git diff --check` is clean for touched test files, and graphify is updated after code changes.

## Remediation Closure
- **Status:** Closed on 2026-08-13.
- **Validation:** Full test suite passed: `1182 passed in 41.49s`.
- **Structured-query scope:** Planner, bounded SQLite executor, and Workspace Chat adapter were audited with a realistic multi-sheet workbook containing Unicode, punctuation, dates, combined filters, aggregation, and cross-sheet provenance.
- **Security and bounds:** SQL remains allow-listed and parameterized; workbook query limits remain `max_cells=100000` and `max_rows=50`; unsupported/ambiguous requests fail soft.
- **Graph:** `graphify update .` completed after the code changes. Its scan skipped only inaccessible generated `pytest_goal_032` and `pytest_goal_033` directories.
