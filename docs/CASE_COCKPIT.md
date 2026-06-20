# AIOS Case Cockpit v0.1

The **AIOS Case Cockpit** is a local UI designed for handling specific support or development "cases".

## Features
- **Case Management**: Create, track, and update the status and priority of individual cases.
- **Evidence Ingestion**: Upload Excel/CSV spreadsheets and image screenshots directly to the case. Add logs and chat pastes seamlessly.
- **Visual Case Map**: Generates a local architecture graph of how case evidence and hypotheses connect.
- **Rule-based Next Actions**: Suggests next steps depending on what is missing from the case investigation.
- **AI Prompt Pack**: Safely formats the case situation, logs, and evidence into a copyable prompt for external LLMs (ChatGPT, Gemini, Copilot, NotebookLM), while rigorously preventing the inclusion of `local_only` raw data in cloud prompts.
- **Handover Generation**: Quickly print the case status for team handover.

## Data Storage
All case data and uploaded assets are stored strictly in `local_cases/` at the repository root. This directory is git-ignored and ensures total privacy.

## Launching
- Run `RUN_AIOS_CASE_COCKPIT.bat`
- Or use `.\scripts\run_case_cockpit.ps1`
- Or run `py -3 -m streamlit run src\aios_habit\case_cockpit.py`

## Privacy & Security Hardening
- **Prompt Privacy**: `local_only` evidence and raw `SeniorLearningCard` text are strictly excluded from cloud/external prompt targets (`gemini`, `gpt`, `copilot`, `notebooklm_safe`) by default. The `local_ai` target may include `local_only` evidence/cards only if `include_local_only=True` is explicitly specified.
- **Audit Helper**: The Audit tab calls a testable verification helper that checks case title completeness, situation completeness, asset containment path safety (strictly inside `local_cases/assets`), and makes sure `local_only` evidence and unconfirmed learning card texts are never leaked in external prompts.
- **Input Validation**: Empty titles and empty note contents are verified and blocked at the UI layer to keep the case database clean.
- **Asset Sanitization**: Uploaded files have their names normalized and prefixed with millisecond-based timestamps to prevent directory traversal attacks and namespace collisions.

## Senior Learning Card / Thẻ học nghề
AIOS không tự học vô kiểm soát. Hệ thống đề xuất và lưu trữ bài học có cấu trúc (gồm triệu chứng, giả thuyết, chuỗi nhân quả, nguyên nhân thật, đối sách, bài học tái sử dụng, điều kiện áp dụng), nhưng người dùng phải kiểm chứng và chuyển trạng thái xác nhận (`confirmed`) trước khi bài học được coi là kinh nghiệm đáng tin để tái sử dụng.

## UI Language Policy
The user interface is fully localized in Vietnamese to serve local operators, following the guidelines in [UI_LANGUAGE_POLICY.md](UI_LANGUAGE_POLICY.md). English technical constants (like `local_only`) are annotated with inline explanations.

