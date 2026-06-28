# Non-Excel NotebookLM vs AIOS 2Q Report

## Baseline
- Branch: `main`
- HEAD before benchmark: `20a194c`
- Origin/main before benchmark: `20a194c`
- Real MOM docs used locally: YES, from ignored local folder only
- Output folder: `local_runs/notebooklm_vs_aios_non_excel_2q/` (ignored)
- Raw docs committed: NO
- Raw extracted chunks committed: NO
- Raw AIOS answers committed: NO
- Raw NotebookLM answers committed: NO

## Questions
1. Q1, target PDF/PPTX:
   "Từ các tài liệu PPTX/PDF về MOM/AMS, hãy giải thích quy trình thao tác hoặc luồng nghiệp vụ chính, và chỉ rõ điểm nào cần xử lý thủ công thay vì hệ thống tự động."
2. Q2, target PNG/JPG/HTML:
   "Dựa trên screenshot/HTML/ERD trong bộ tài liệu, hãy cho biết màn hình hoặc sơ đồ thể hiện những bảng, trường, quan hệ hoặc trạng thái nào có thể dùng làm bằng chứng vận hành; điểm nào không được suy luận nếu chỉ nhìn ảnh/sơ đồ."

## AIOS Run
- AIOS retrieval/search run: YES
- Targeted evidence packs built: YES
- Local Evidence Drafts generated: YES
- Strong Answer prompt packs generated: YES
- Direct cloud provider call made: NO
- Direct provider call blocked for `local_only`: YES
- Manual strong-answer mode required: YES
- NotebookLM used as ground truth: NO

## Q1 AIOS Evidence
- Primary evidence type: PDF/PPTX
- Source selection: PASS
- Evidence quality: `content_supported`
- Confidence label: `high`
- Content evidence count: 10
- Metadata-only evidence count: 0
- Top evidence files:
  - `AMS概略フロー_入出庫・生産_20250703VN.pdf` (`.pdf`)
  - `AMS_設計変更.pdf` (`.pdf`)
  - `KDTVN_AMS対応でのMES設定箇所 1.pptx` (`.pptx`)
- AIOS answer summary: AIOS retrieved process-oriented AMS/MOM PDF evidence first, with supporting PPTX evidence for MES-related configuration context. The safe summary is that AIOS can draft a source-cited explanation of the main AMS/MOM operational flow and flag manual-review/manual-operation areas, but the final wording should remain evidence-limited and owner-reviewed.
- Missing evidence/risk: The top hits are PDF-heavy. This is valid for Q1, but the manual-vs-automatic distinction should not be overclaimed unless the owner confirms the cited pages/slides.

## Q2 AIOS Evidence
- Primary evidence type: PNG/JPG/HTML
- Source selection: PASS
- Evidence quality: `content_supported`
- Confidence label: `high`
- Content evidence count: 10
- Metadata-only evidence count: 0
- OCR available: YES
- Top evidence files:
  - `ERD_Kho_Van.html` (`.html`)
  - `WMS/Screenshot 2026-03-20 183509.png` (`.png`)
  - `システム構成図r3_2026-4-10.png` (`.png`)
  - `WMS/Screenshot 2026-03-20 183202.png` (`.png`)
  - `WMS/Screenshot 2026-03-20 183911.png` (`.png`)
- AIOS answer summary: AIOS retrieved HTML ERD evidence first, then screenshot/OCR evidence. The safe summary is that AIOS can cite visible schema/screen evidence for operational traceability, while explicitly refusing to infer hidden business rules, unseen field semantics, or state transitions not visible in the ERD/screenshot evidence.
- Missing evidence/risk: Screenshot OCR is useful but weaker than structured HTML. Treat OCR-derived evidence as review-required.

## NotebookLM Status
- NotebookLM CLI available: YES
- NotebookLM answers actually collected: NO
- Reason: No owner-confirmed existing NotebookLM notebook ID containing the same MOM documents was provided. This task did not upload raw MOM documents and did not send company source content to NotebookLM.
- Owner manual step required: YES
- Exact owner questions to ask in the already-approved NotebookLM notebook:
  - Q1: "Từ các tài liệu PPTX/PDF về MOM/AMS, hãy giải thích quy trình thao tác hoặc luồng nghiệp vụ chính, và chỉ rõ điểm nào cần xử lý thủ công thay vì hệ thống tự động."
  - Q2: "Dựa trên screenshot/HTML/ERD trong bộ tài liệu, hãy cho biết màn hình hoặc sơ đồ thể hiện những bảng, trường, quan hệ hoặc trạng thái nào có thể dùng làm bằng chứng vận hành; điểm nào không được suy luận nếu chỉ nhìn ảnh/sơ đồ."

## Scoring
NotebookLM answers were not collected, so NotebookLM is not scored and no winner is declared.

| Question | AIOS Score | NotebookLM Score | Winner | Notes |
| --- | ---: | ---: | --- | --- |
| Q1 | N/A | N/A | INCONCLUSIVE | AIOS source selection passed on PDF/PPTX; owner NotebookLM answer missing. |
| Q2 | N/A | N/A | INCONCLUSIVE | AIOS source selection passed on HTML/PNG; owner NotebookLM answer missing. |

## Overall Result
- Overall result: inconclusive
- NotebookLM parity claimed: NO
- If parity claimed: N/A
- P1.0 opened: NO
- Main weakness: NotebookLM manual answers are missing, so this is not a completed head-to-head comparison.
- Recommended next step: OWNER_NOTEBOOKLM_MANUAL_2Q_COMPARE

## Validation Before Report
- `py -3 -m pytest tests/test_document_extractors.py -vv`: PASS
- `py -3 -m pytest tests/test_rag_search.py -vv`: PASS
- `py -3 -m pytest tests/test_rag_evaluator.py -vv`: PASS
- `py -3 -m pytest tests/test_strong_answer_ui.py -vv`: PASS
- `py -3 -m pytest`: PASS, 359 passed
- Package import: PASS
- CLI audit: PASS
- `local_runs` ignored: YES
- `API Key.txt` ignored: YES
- Real docs/runtime/secrets tracked by safety pattern: NO

## Safety
- Whole folder included in prompt: NO
- Automatic provider call made: NO
- API keys printed: NO
- Raw docs committed: NO
- Raw answers committed: NO
- `local_runs` committed: NO
- Screenshots committed: NO

## Verdict
PASS_AIOS_READY_FOR_NOTEBOOKLM_MANUAL_COMPARE
