# Strong Answer UI Implementation Design

## Current Case Cockpit UI structure
- `case_cockpit.py` is Streamlit-based.
- Main export workflow is `page_prompt_pack()` under `🧪 Xuất kết quả`.
- Existing prompt-pack UI already teaches users to copy/paste prompt text safely.
- Case evidence is loaded from `load_evidence()` and filtered by active `case_id`.

## Best place for controls
- Add a minimal subsection inside `page_prompt_pack()` after the existing prompt area.
- This keeps owner workflow in the existing export/copy-paste page and avoids a redesign.

## Privacy constraints
- Local-only evidence must not trigger automatic cloud calls.
- UI only prepares a bounded prompt pack.
- If evidence pack privacy is `local_only`, direct provider/cloud call is blocked and a warning is shown.

## Manual paste-back flow
1. Owner enters question.
2. AIOS creates a Local Evidence Draft from case evidence.
3. AIOS exports a strong-model prompt pack for manual copy/paste.
4. Owner pastes the model/tool answer back.
5. AIOS stores pasted answer as `pasted_strong_model_answer` evidence.

## Non-goals
- No PPTX adapter.
- No image OCR adapter.
- No vector DB or graph DB.
- No automatic cloud call for local-only evidence.
- NotebookLM parity claimed: NO.
- P1.0 opened: NO.
