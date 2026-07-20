# Gate A18 — NotebookLM Comparison Arena Prompt

Bạn là implementation executor cho repo `AIOS_habbit`.

## Mục tiêu

Tạo comparison arena để owner so sánh câu trả lời AIOS và NotebookLM trên cùng câu hỏi/nguồn đã được phép. Owner tự cung cấp NotebookLM answer/export bằng tay. Không scraping hoặc tự động điều khiển NotebookLM.

Đọc trước:

- `docs/design/AIOS_BRAIN_GATEWAY_DESIGN.md`
- `docs/design/AIOS_EXISTING_AI_INVENTORY.md`
- `docs/MOM_NOTEBOOKLM_COMPARISON_MVP.md`
- `docs/NOTEBOOKLM_MANUAL_COLLECTION_RUNBOOK.md`

## Nguyên tắc privacy

- Không gửi `local_only`/`confidential` ra cloud.
- Thiếu privacy metadata hoặc mixed nguồn nhạy cảm: deny cloud.
- AIOS answer dùng Local Brain, hoặc Router Brain chỉ khi privacy/consent cho phép.
- NotebookLM answer do owner nhập thủ công; AIOS không tự upload source.
- Không commit raw answer/company content; runtime output ở ignored local directory.
- Không tự tuyên bố NotebookLM parity hay “AIOS tốt hơn”.

## Input contract

- arena/run ID;
- question;
- AIOS answer + evidence/citation refs + brain/route summary;
- owner-supplied NotebookLM answer;
- optional owner-supplied NotebookLM citations/export metadata;
- privacy class;
- source-set fingerprint;
- evaluator version.

Không yêu cầu raw local document trong comparison record nếu evidence refs đã đủ. Nếu owner paste nội dung nhạy cảm, record phải giữ local và bị chặn export.

## Tiêu chí so sánh

Chấm riêng từng câu trả lời và ghi bằng chứng/nhận xét:

1. evidence coverage;
2. cited source alignment;
3. missing facts;
4. hallucination risk;
5. actionable next steps;
6. Vietnamese clarity.

Mỗi tiêu chí cần score có thang rõ, rationale và trạng thái `human_review_required`. Không dùng score tổng để tự động công bố winner.

## Hành vi khi thiếu dữ liệu

- Không có NotebookLM answer: run ở trạng thái `WAITING_OWNER_INPUT`.
- Không có citation: chấm source alignment là `NOT_EVALUABLE`, không tự cho 0 hoặc PASS.
- Privacy không hợp lệ: `BLOCKED_PRIVACY`.
- AIOS route fail: lưu explicit no-answer/local fallback, không âm thầm gọi cloud.
- Input khác source-set: `INVALID_COMPARISON`.

## Reuse

Tái sử dụng evaluator/schema concepts từ `notebooklm_compare.py` nhưng không tự động chạy `nlm`, không `subprocess` cho NotebookLM và không ghi raw output vào tracked files.

## Tests bắt buộc

- owner manual answer import;
- missing answer/citation states;
- source-set mismatch;
- six comparison dimensions;
- Vietnamese Unicode round-trip;
- local-only/confidential cloud denial;
- Router Brain chỉ được gọi qua mock khi allowed;
- no NotebookLM scraping/process/network;
- no raw sentinel trong exportable summary;
- no automatic parity/winner claim.

## Validation

```powershell
git diff --name-only
git diff --stat
git diff --check
uv run --no-sync pytest -q
$env:PYTHONPATH="src"; uv run --no-sync python -m aios_habit.cli audit
py -m compileall src scripts
git status --short -- .ai local_cases task.md walkthrough.md implementation_plan.md
```

Không commit/push nếu owner chưa phê duyệt.

## Output

```text
FINAL_STATUS:
BASELINE:
ARENA_SCHEMA:
PRIVACY_BEHAVIOR:
COMPARISON_DIMENSIONS:
MANUAL_NOTEBOOKLM_FLOW:
FILES_TOUCHED:
VALIDATION:
RUNTIME_DIRTY:
CLAIM_POLICY:
COMMIT_CREATED: NO (trừ khi owner phê duyệt)
PUSH_PERFORMED: NO
NEXT_STEP:
```
