# AIOS Agent Result Import Design

## Mục tiêu

Agent Result Import biến report không đáng tin thành một kết quả có kiểm chứng để hiển thị trong AIOS case. Importer không tin `PASS` chỉ vì agent tự khai.

## Pipeline

```text
report file
  -> parse + schema/size validation
  -> bind task_id/task-pack hash
  -> normalize fields
  -> inspect local repo evidence
  -> detect scope/fake PASS
  -> verdict
  -> case summary
  -> optional draft Senior Learning Card
```

Không thực thi command, script hoặc path instruction nằm trong report.

## Dữ liệu cần trích xuất

- final status do agent khai;
- branch, baseline head, final head;
- commit hash nếu có;
- files touched, staged, committed, untracked;
- test commands, exit codes, counts và result;
- audit result;
- forbidden touched;
- runtime dirty;
- risks và next step;
- agent class, model/tool, timestamps;
- report/task-pack hash.

## Đối chiếu local evidence

Khi repo còn khả dụng, importer chạy/read-only checks theo task policy:

- `git branch --show-current`;
- `git rev-parse HEAD`;
- `git status --short`;
- `git diff --name-only`, cached và commit file list nếu có;
- xác minh commit tồn tại và parent/baseline;
- không chạy lại test tự động trừ khi owner/task pack cho phép.

Report và observed state được lưu riêng. Mismatch không bị ghi đè.

## Phát hiện scope violation

Scope violation khi:

- file touched không match `allowed_files`;
- file match `forbidden_files`;
- command ngoài allow-list;
- branch/head baseline sai và không có exception;
- commit/push xảy ra khi task không cho;
- `.ai`/`local_cases` hoặc runtime file dirty ngoài explicit allowance;
- report task ID/hash không khớp pack;
- agent tự giảm required test hoặc sửa PASS rule.

Severity:

- forbidden write, secret access, unauthorized push: `FAIL`;
- mismatch cần owner xác minh nhưng chưa có write nguy hiểm: `REVIEW_REQUIRED`;
- không có violation và đủ evidence: có thể PASS.

## Phát hiện fake PASS

Các tín hiệu bắt buộc:

1. **Thiếu test evidence**: ghi PASS nhưng thiếu command, exit code hoặc result cho required test.
2. **Test count đổi không giải thích**: collected/passed khác baseline/expected mà report không nêu lý do.
3. **Forbidden dirty**: file cấm hoặc runtime dirty.
4. **Untracked scratch**: file untracked không được allow.
5. **Claim không có command**: nói audit/compile/test pass nhưng `commands_run` không có bằng chứng.
6. **Head/commit không khớp**: commit khai báo không tồn tại hoặc không chứa files được khai.
7. **PASS với failed/skipped required test**.
8. **Output summary tự mâu thuẫn**: status PASS nhưng risks nêu blocker.

Importer tạo `fake_pass_flags[]` với reason code, không suy diễn bằng text tự do duy nhất.

## Verdict đề xuất

```text
VERIFIED_PASS
REVIEW_REQUIRED
FAIL_SCOPE_VIOLATION
FAIL_VALIDATION
FAIL_MALFORMED_REPORT
```

`VERIFIED_PASS` chỉ nghĩa là report khớp task pack và evidence quan sát được; không tự động merge/push hoặc xác nhận chất lượng sản phẩm.

## Import vào AIOS case

Tạo case event/evidence summary gồm:

- task ID, verdict, agent-declared status;
- branch/head/commit;
- files touched;
- validation summary;
- scope/fake-pass flags;
- risks và next step;
- link/path local tới report đã xử lý;
- importer version và timestamp.

Raw report có thể chứa thông tin nhạy cảm nên lưu theo privacy của task, không tự export cloud. UI phải phân biệt “Agent báo PASS” và “AIOS đã kiểm chứng PASS”.

## Senior Learning Card tùy chọn

Chỉ tạo **draft** card khi owner chọn và report có lesson có thể tái sử dụng. Không bao giờ:

- tạo card `confirmed` tự động;
- biến agent claim thành verified evidence;
- chép raw secret/company content vào card cloud-safe;
- tạo card khi verdict malformed/scope violation.

Draft card cần link task/case/commit/test evidence và trường `review_required=true`. Owner xác nhận ở workflow riêng.

## Security

- giới hạn kích thước report và độ sâu JSON;
- UTF-8 strict, không sửa mojibake im lặng;
- normalize path rồi kiểm containment;
- không follow path ngoài repo do report cung cấp;
- redact secret-like strings trong UI/audit;
- không deserialize object tùy ý;
- không checkout/reset/move/delete;
- report import là read-only với repo, trừ ghi case artifact được owner workflow cho phép.

## Test strategy

- parse report hợp lệ và aliases versioned;
- malformed JSON/Markdown, missing status/head/files/tests;
- PASS thiếu required test;
- test count mismatch;
- forbidden/runtime dirty và untracked scratch;
- commit hash giả/mismatch;
- unauthorized commit/push;
- observed state khác report;
- path traversal/symlink escape;
- secret sentinel không xuất hiện trong safe summary;
- Senior Learning Card luôn draft/review-required.
