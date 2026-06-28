# Strong Answer UI Button Report

## What was added
- Added a minimal Case Cockpit section: **Trả lời bằng AI mạnh từ bằng chứng**.
- Added reusable helpers in `strong_answer_ui.py` for local evidence draft, prompt export, and pasted-answer save.
- No provider/cloud call is performed by the UI helpers.

## Owner 3-step usage
1. Enter a question and click **1. Tạo bản nháp bằng chứng local**.
2. Click **2. Tạo prompt cho Gemini/Codex/Claude** and copy the prompt manually.
3. Paste the model answer, enter model/tool name, and click **3. Lưu câu trả lời AI mạnh vào hồ sơ**.

## Privacy behavior
- Local Evidence Draft is clearly marked as not final.
- Local-only evidence blocks automatic cloud/provider calls.
- Prompt export shows: `Tự động gọi cloud bị chặn vì dữ liệu local_only...`
- Pasted strong answer becomes final only when answer text and evidence refs exist.

## Safety
- Raw docs committed: NO.
- Raw answers committed: NO.
- NotebookLM parity claimed: NO.
- P1.0 opened: NO.

## Remaining before P1.0
- Owner acceptance run.
- PPTX/Image extraction remains optional/future.
- Evaluator quality improvement.
- UI usability check.
