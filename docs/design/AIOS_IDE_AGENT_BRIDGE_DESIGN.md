# AIOS IDE Agent Bridge Design

## Vai trò

IDE agents là executor có scope và bằng chứng, không phải memory store, nguồn chân lý hay actor tự trị. Bridge chỉ:

1. xuất task pack;
2. để owner chuyển pack tới agent phù hợp;
3. nhập report/result;
4. kiểm scope, git state, test evidence và privacy;
5. đưa kết quả vào case ở trạng thái phù hợp.

A17 không tự chạy agent, không launch external process, không push và không đọc secret.

## Task pack format

Task pack nên là JSON có schema version kèm Markdown dễ đọc:

```text
schema_version
task_id
agent_class
objective
repo_path
expected_branch
expected_head
allowed_files[]
forbidden_files[]
allowed_commands[]
forbidden_commands[]
required_tests[]
required_report_fields[]
pass_fail_rule
anti_overeager_rule
privacy_class
owner_approval
created_at
pack_sha256
```

### Trường bắt buộc

- **Repo path**: absolute local path cho executor; không đưa cloud nếu privacy không cho phép.
- **Branch/head**: baseline phải được report lại; mismatch là stop/fail.
- **Allowed files**: glob/file chính xác; mặc định không cho write ngoài danh sách.
- **Forbidden files**: tối thiểu `.ai/**`, `local_cases/**`, secret/config/key files, và các file owner khóa.
- **Allowed commands**: allow-list; lệnh ngoài danh sách cần owner approval mới.
- **Required tests**: command và expected outcome; không được thay số test im lặng.
- **Required report fields**: status, baseline/final head, files touched, commands/tests, commit, risks, next step.
- **PASS/FAIL rule**: PASS chỉ khi scope sạch, required validation có evidence và không có forbidden dirty.
- **Anti-overeager rule**: không mở rộng scope, refactor tiện tay, sửa test để che lỗi, commit/push khi chưa được phép.
- **No secret/key access**: không đọc/echo env secrets, key files, credential stores hay Authorization headers.
- **Runtime cleanliness**: `.ai` và `local_cases` không dirty trừ khi task pack nêu rõ và owner cho phép.

## Agent classes

| Class | Quyền | Output chính | Không được làm |
|---|---|---|---|
| `audit-only` | Read, chạy lệnh audit/test allow-listed | Findings, PASS/FAIL có evidence | Sửa runtime/code |
| `implementation` | Sửa allowed files, chạy required tests | Diff, test evidence, risks | Push; sửa ngoài scope |
| `push-safety` | Read-only verification của commit/worktree/remote | Ready/not-ready verdict | Sửa code hoặc push nếu task không cho |
| `smoke-test` | Chạy smoke allow-listed, thu safe evidence | Observed behavior | Dùng real secret/data ngoài approval |

## Output/report format

```text
schema_version
task_id
status: PASS | FAIL | REVIEW_REQUIRED
branch
baseline_head
final_head
commit_hash: optional
files_touched[]
commands_run[]:
  command, exit_code, started_at, duration_ms, safe_output_summary
tests[]:
  command, result, collected, passed, failed, skipped
audit_result
forbidden_touched[]
runtime_dirty[]
untracked_files[]
risks[]
next_step
agent_class
model_tool_name
report_sha256
```

`safe_output_summary` không chứa secret/raw company data. Khi có commit, report phải phân biệt files touched trong worktree và files thuộc commit.

## PASS/FAIL semantics

PASS yêu cầu đồng thời:

- branch/head baseline đúng hoặc divergence đã được task cho phép;
- chỉ file allow-listed thay đổi;
- forbidden/runtime clean;
- required commands thật sự chạy và exit code phù hợp;
- test counts có thể giải thích;
- không có untracked scratch;
- claims có command/evidence;
- commit/push state đúng authorization.

Thiếu evidence không phải PASS; dùng `REVIEW_REQUIRED` hoặc FAIL theo task rule.

## Privacy và trust

- Coding task không tự động đồng nghĩa cloud-safe.
- `local_only/confidential`: chỉ local/manual IDE agent đã được owner phê duyệt.
- Task pack cloud không chứa raw evidence/company docs.
- Agent không được truy cập key/secret để “tự cấu hình”.
- Report import không thực thi command từ report.
- Pack/report dùng schema validation, size limit, safe path handling và hash.
- Agent output là untrusted input cho tới khi importer kiểm chứng bằng local git/test evidence.

## Model guidance

Đây là hướng dẫn chọn executor, không phải hard-coded routing:

- **Codex GPT-5.5**: audit, review, kiểm scope, anti-fake PASS.
- **Gemini Pro/Flash**: implementation, UI và fix nhạy encoding khi owner chọn.
- **Local/manual**: mọi task có confidential/local-only hoặc khi external use chưa được consent.

Capability, privacy và owner approval luôn ưu tiên hơn tên model.

## Tái sử dụng bridge hiện có

`ide_bridge.py` và `ide_handoff_bridge.py` đã có prompt pack, evidence allow-list, checksum, outbox/inbox và paste-back validation. A17 nên:

- giữ answer-handoff schema tương thích;
- thêm task-pack schema riêng cho repo work;
- không nhét git/task fields vào evidence-answer schema một cách mơ hồ;
- dùng cùng request ID/hash/audit conventions;
- import về Brain Gateway/Agent Result Import trước khi lưu case.

## Test strategy A17

- round-trip task pack UTF-8;
- reject missing required field/schema version;
- reject branch/head mismatch;
- detect touched file ngoài allow-list;
- detect `.ai`, `local_cases`, forbidden file dirty;
- detect untracked scratch;
- PASS/FAIL/REVIEW_REQUIRED parsing;
- test count change không giải thích;
- missing command/exit code;
- secret-looking content bị redact/reject;
- không launch process và không network;
- không commit/push trong test.
