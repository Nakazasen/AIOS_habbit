# Implementation Plan: Excel Structured Query Audit 3 Remediation

## Proposed Changes

### `src/aios_habit/rag_v2/structured_query.py`

1. **Bounded all-sheets detection**
   - Add a focused helper that detects canonical `tat ca` and standalone token `all`.
   - Replace both substring checks in `plan_excel_query()` so words such as `smallest` cannot enable `target_regions`.

2. **Lossless aggregate provenance records**
   - Replace comma-separated aggregate metadata with an internal SQLite provenance record:
     `sheet + field-separator + cell-range + field-separator + row`, joined by a record separator.
   - Use ASCII control separators that cannot appear in Excel sheet names, then parse each record into its own `StructuredProvenance`.
   - Preserve exact rows and ranges for each contributing sheet/region, eliminating the earlier cross-sheet row-list reuse.

### `src/aios_habit/workspace_chat_rag_v2_adapter.py`

- No production adapter changes are expected; retain its provenance-derived multi-sheet location behavior and cover it through the managed-workbook integration path.

### Test Coverage & Hygiene

#### `tests/test_rag_v2_structured_query.py`
- Add regressions for `smallest Revenue` not matching `all`.
- Add a legal comma-containing sheet-name aggregate test verifying `East,West` remains a single provenance sheet.

#### `tests/test_workspace_chat_rag_v2_adapter.py`
- Add managed-workbook multi-sheet integration coverage verifying `location_info == "Sheets: East, West"` and a multi-region rendered header.

#### Test file hygiene
- Remove trailing blank EOF lines in the two previously flagged test files.

## Verification Plan

```powershell
.venv\Scripts\python.exe -m py_compile `
  src/aios_habit/rag_v2/structured_query.py `
  src/aios_habit/workspace_chat_rag_v2_adapter.py

.venv\Scripts\python.exe -m pytest `
  tests/test_rag_v2_structured_query.py `
  tests/test_workspace_chat_rag_v2_adapter.py `
  tests/test_workspace_chat_ai_answer.py `
  tests/test_workspace_chat_multi_file_uploader.py -q

git diff --check -- tests/test_workspace_chat_multi_file_uploader.py tests/test_workspace_chat_rag_v2_adapter.py
graphify update .
```

### Audit Probes
- `smallest Revenue` on matching `East`/`West` schemas fails soft as ambiguous, never sets `target_regions`.
- Aggregate over `East,West` and `North` preserves provenance sheets exactly as `("East,West", "North")`.
- Managed Workbook route emits the expected multi-sheet citation location.
