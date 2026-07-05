# AIOS IDE Agent Bridge Design

## 1. Vai trò & Ranh giới (Architecture & Boundaries)

IDE Agent Bridge đóng vai trò là một control plane (mặt phẳng điều khiển) cho các tác vụ thay đổi repo (repo tasks). IDE Agent (hoặc AI agent) chỉ là một executor (bộ thực thi) có phạm vi (scope) và bằng chứng xác thực, không phải là một memory store (kho lưu trữ bộ nhớ), không phải là nguồn chân lý (source of truth) và không phải là một actor tự trị (autonomous actor).

### Ranh giới thiết kế cốt lõi

- **Không tự động chạy agent:** Hệ thống không tự động khởi chạy các agent bên ngoài, không mở các process/subprocess, không chạy script tùy ý nhận được từ bên ngoài.
- **Không tự động chạy test hoặc command trên importer:** Importer chỉ làm nhiệm vụ parse/validate cấu trúc dữ liệu của report và đối chiếu dữ liệu có sẵn. Importer không tự chạy bất kỳ test hay command nào. Mọi hoạt động test/validation thực tế trên repo chỉ được thực thi qua một owner-triggered verifier/observer cục bộ hoàn toàn độc lập và tách biệt. Nếu chưa có kết quả kiểm chứng độc lập từ owner-triggered observed evidence, verdict tối đa của quá trình import chỉ có thể là `REVIEW_REQUIRED`. Tại subgate `AI-GW-A17D`, hệ thống mới được phép tích hợp read-only Git/test observer cố định, tuy nhiên bộ verifier/observer này vẫn phải được kích hoạt trực tiếp bởi owner (owner-triggered) và tuyệt đối không tự động đọc hay thực thi các command trích xuất từ file report của agent. Mọi observed-evidence receipt bắt buộc phải chứa các trường provenance chứng minh command/test đến từ cấu hình cố định của owner (`command_source` phải là `OWNER_APPROVED_FIXED_CONFIG`, `command_from_report` là `false`, `report_command_ignored` là `true`).
- **Không tự động gọi mạng hoặc API của provider thật:** Bridge không có quyền gọi bất kỳ provider hay router thật nào (các legacy modules như `llm_client.py`, `ai_provider_bridge.py`, `ai_router.py`, `notebook_qa.py` là direct network/provider paths tiềm ẩn rủi ro; A17 không được kích hoạt, gọi, hoặc phụ thuộc vào chúng).
- **Không tự động commit/push:** Importer không tự động tạo commit hoặc push lên GitHub. Mọi thao tác ghi/nhận phải thông qua owner workflow phê duyệt và kiểm chứng thủ công.
- **Không tự động mở P1.0:** Trạng thái P1.0 vẫn khóa chặt (LOCKED) và không bị ảnh hưởng bởi thiết kế hay hoạt động của Bridge.
- **Phân tách ranh giới UI:** Workspace Chat là giao diện chính (primary UI) duy nhất để giao tiếp và import/export về sau. Case Cockpit chỉ đóng vai trò là một reference/debug component cũ, không đưa UI A17 trở lại Case Cockpit.
- **Ranh giới với Brain Gateway:** Brain Gateway cung cấp các khái niệm về chính sách bảo mật, phân loại dữ liệu (privacy/policy concepts), và strictest-wins. Nó không đóng vai trò làm Git verifier hay bộ phân tích kết quả (report parser) của Bridge.
- **Khác biệt với Manual Handoff:** Manual answer/evidence bridge (cầu nối câu trả lời/bằng chứng thủ công thông qua paste-back answer hiện có) hoạt động độc lập và hoàn toàn khác biệt với cấu trúc repo-task pack bridge có quản lý phiên bản và mã hóa toàn vẹn dữ liệu trong A17.

---

## 2. Thiết kế Task Pack Schema (`aios_agent_task_pack_v1`)

Mỗi task pack được xuất ra dưới định dạng JSON deterministic để đảm bảo tính toàn vẹn và có thể phân tích dễ dàng bởi các agent executor.

### Cấu trúc Schema JSON

```json
{
  "schema_version": "aios_agent_task_pack_v1",
  "task_id": "A17_TASK_EXPORT_001",
  "task_type": "implementation | audit | smoke-test | push-safety",
  "gate": "AI-GW-A17A",
  "agent_class": "audit-only | implementation | push-safety | smoke-test",
  "objective": "Detailed description of the programming or auditing objective",
  "repo": {
    "logical_repo_id": "AIOS_habbit_main",
    "repo_path_policy": "local_absolute | logical_relative",
    "expected_branch": "main",
    "expected_head": "f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039"
  },
  "scope": {
    "allowed_files": [
      "src/aios_habit/workspace_chat_app.py",
      "tests/test_workspace_chat_app.py"
    ],
    "forbidden_files": [
      ".ai/**",
      "local_cases/**",
      "task.md",
      "walkthrough.md",
      "implementation_plan.md",
      "config/secrets.json"
    ],
    "allowed_commands": [
      "uv run pytest",
      "git status"
    ],
    "forbidden_commands": [
      "git push",
      "curl",
      "rm -rf"
    ],
    "required_tests": [
      "tests/test_workspace_chat_app.py"
    ]
  },
  "privacy": {
    "privacy_class": "local_only | confidential | machine_only | cloud_safe | public",
    "destination": "local_manual_agent | owner_managed_chat",
    "purpose": "Code implementation and test verification",
    "consent_ref": "consent-snapshot-hash-or-id",
    "source_policy": "redact_raw_contents | allow_sanitized_derivative"
  },
  "roadmap_reference": {
    "phase": "Phase 4 — Workspace Chat Foundation & AI Gateway Preparation",
    "gate": "AI-GW-A17",
    "lock_status": "P1.0 LOCKED"
  },
  "pass_fail_rules": [
    "No forbidden files modified",
    "All required tests passed with correct exit codes",
    "No untracked files in scratch directory"
  ],
  "rollback": {
    "allowed": true,
    "strategy": "manual_git_discard_by_owner",
    "description": "Rollback bắt buộc phải do owner thực hiện thủ công bằng lệnh git (không tự động chạy). Quá trình này có khả năng làm mất các thay đổi cục bộ chưa commit, vì vậy bắt buộc phải kiểm tra git status trước khi thực hiện. Agent không được tự ý thực hiện rollback nếu không có sự phê duyệt nhiệm vụ (task approval) rõ ràng từ owner."
  },
  "required_report_fields": [
    "schema_version",
    "task_id",
    "task_pack_sha256",
    "agent_class",
    "model_tool_name",
    "declared_status",
    "baseline.branch",
    "baseline.head",
    "final_state.branch",
    "final_state.head",
    "final_state.commit_hash",
    "final_state.push_status",
    "declared_files.changed",
    "declared_files.staged",
    "declared_files.untracked",
    "declared_files.committed",
    "declared_commands",
    "declared_tests",
    "risks",
    "blockers",
    "rollback",
    "reason_codes",
    "report_sha256"
  ],
  "created_at": "2026-07-05T15:21:22Z",
  "pack_sha256": "computed-sha256-hex-hash"
}
```

### Quy tắc băm và Bảo vệ (Hash Rules)

- **Bản chất của SHA-256:** SHA-256 đóng vai trò là một integrity hash/checksum để kiểm tra tính toàn vẹn của tệp tin, tuyệt đối không phải là một chữ ký số (digital signature) có tính xác thực nguồn gốc. Nếu cần tính xác thực (authenticity) và chống chối bỏ sau này, hệ thống sẽ yêu cầu một signing scheme riêng biệt và nằm ngoài phạm vi của A17 MVP.
- **Thuật toán băm toàn vẹn:** Sử dụng **SHA-256** làm hàm băm duy nhất. **Tuyệt đối không dùng MD5** làm integrity hash cho A17.
- **Wording Destination:** Trường `destination` trong task pack (ví dụ: `local_manual_agent`, `external_manual_agent`, `owner_managed_chat`) chỉ đóng vai trò là chính sách bảo mật / phân phối (policy metadata) phục vụ cho owner-managed workflow, tuyệt đối không phải là một đối tượng thực thi (execution target). Bridge không tự động gọi router hay provider thật.
- **Tính toán băm:** Hàm băm `pack_sha256` được tính dựa trên chuỗi JSON canonical (sort keys, compact separators không có khoảng trắng thừa, mã hóa UTF-8, không có Byte Order Mark (BOM)).
- **Tự loại trừ:** Khi tính toán băm, trường `"pack_sha256"` phải được loại bỏ khỏi đối tượng JSON.

### Chính sách đường dẫn Repo (Repo Path Policy)

- **Local/Manual Task Packs:** Có thể chứa absolute repo path nếu như mức độ bảo mật (privacy_class) cho phép (ví dụ: chạy cục bộ hoàn toàn trên máy của Owner).
- **Cloud Task Packs:** Tuyệt đối không chứa absolute repo path thực tế trên đĩa cứng; thay vào đó, chỉ được sử dụng `logical_repo_id` (ví dụ: `AIOS_habbit_main`) và các đường dẫn tương đối (relative paths) bắt đầu từ gốc thư mục làm việc.
- **Không rò rỉ dữ liệu nhạy cảm:** Không chứa username, local path của các file hệ thống, không đính kèm raw source code, secrets, nội dung các file bỏ qua (ignored files), các thư mục quản trị nội bộ của hệ điều hành như `.ai/`, `local_cases/` hay các file runtime JSON.

---

## 3. Phân loại Executor (Agent Classes)

| Class | Quyền hạn | Output chính | Không được phép làm |
| --- | --- | --- | --- |
| `audit-only` | Quyền đọc, thực thi các lệnh audit/test nằm trong allow-list | Các findings chi tiết, PASS/FAIL kèm evidence | Sửa đổi runtime, thay đổi mã nguồn (write code) |
| `implementation` | Sửa đổi các file thuộc allow-list, chạy required tests | Diff, file patch, test evidence, risks | Thực hiện lệnh git push, sửa đổi file ngoài allowed scope |
| `push-safety` | Quyền đọc để kiểm thử commit, kiểm worktree và remote state | Khẳng định Ready/Not-ready | Sửa code, commit hay push ngoài task authorization |
| `smoke-test` | Khởi chạy smoke tests có trong allow-list, thu thập safe evidence | Observed behavior logs | Sử dụng dữ liệu thật hoặc secrets thật ngoài consent |

---

## 4. Threat Model & Các Rủi ro Bảo mật

Thiết kế của IDE Agent Bridge phải ngăn chặn toàn diện các mối đe dọa sau:

1. **Rò rỉ dữ liệu (confidential/local_only leak):** Leak tài liệu thô hoặc code nội bộ ra cloud thông qua payload gửi đi.
2. **Rò rỉ môi trường máy chủ (local path/username leak):** Lộ tên đăng nhập hệ điều hành, cấu trúc thư mục đĩa cứng qua các task pack xuất ra.
3. **Lộ thông tin nhạy cảm (API key/token leak):** Agent đọc các biến môi trường hoặc key lưu trên file đĩa rồi export ra ngoài.
4. **Vi phạm phạm vi sửa đổi (scope bypass):** Agent cố ý ghi đè các file quan trọng hoặc file cấm (`.ai/`, `local_cases/`, `task.md`...) ngoài scope chỉ định.
5. **Chứng nhận PASS giả (fake PASS):** Agent khai báo PASS nhưng thực tế không chạy test hoặc chỉnh sửa test để che giấu lỗi code.
6. **Lệch baseline (stale HEAD/baseline):** Agent chạy trên một commit cũ hoặc tạo ra trạng thái dirty không khớp với observed state.
7. **Rác trong runtime (dirty runtime/local_cases/untracked scratch):** Xuất hiện các file rác không được kiểm soát sau khi agent chạy xong.
8. **Tấn công hệ thống file (path traversal / symlink escape):** Sử dụng các đường dẫn chứa `../` hoặc symlink độc hại để ghi file ra ngoài thư mục dự án.
9. **Tấn công từ chối dịch vụ (oversized/deep JSON):** Gửi các file report cực lớn hoặc lồng ghép sâu để làm sập bộ nhớ parser.
10. **Tấn công chèn lệnh (command injection / shell interpolation):** Gài mã độc vào trường `commands_run` trong report để lừa importer thực thi lệnh độc hại khi parse.
11. **Tấn công prompt injection:** Độc giả hoặc tài liệu chứa mã độc điều khiển hành vi của agent.
12. **Mojibake / UTF-8:** Lỗi mã hóa ký tự làm méo mó hoặc thay đổi ngữ nghĩa bằng chứng bảo mật.
13. **Accidental commit/push / report replay / wrong-pack:** Gửi lại report cũ, sai pack (wrong-pack), hoặc gói tin stale để ghi đè trạng thái vụ việc (case state).
    - **Replay & Wrong-Pack Control:** Hệ thống yêu cầu report nhận được phải khớp chính xác cả `task_id` và `task_pack_sha256` của tác vụ hiện hành. Nếu không khớp, trả về phán quyết `INVALID_REPORT` với lý do `WRONG_TASK_PACK` hoặc `REPORT_REPLAY_DETECTED`.
    - **Processed Report Ledger:** Hệ thống lưu trữ processed report ledger trong thư mục cục bộ bị git ignore: `local_runs/agent_bridge/processed`.
    - **Idempotency Key:** Khóa trùng lắp duy nhất được tính bằng công thức: `task_id + task_pack_sha256 + report_sha256`. Nếu khóa này đã có mặt trong ledger, report sẽ bị reject ngay lập tức với reason code `REPORT_ALREADY_PROCESSED` hoặc `REPORT_REPLAY_DETECTED` mà không xử lý lại.

---

## 5. Kế hoạch Subgate (Subgate Plan)

Để đảm bảo kiểm soát chất lượng nghiêm ngặt theo mô hình local-first, ranh giới A17 được chia làm các subgates kế hoạch như sau:

1. **AI-GW-A17-DESIGN:** Docs-only design gate (gate hiện tại, chỉ hoàn thiện tài liệu thiết kế hệ thống, không sửa đổi code/test).
2. **AI-GW-A17A:** Task Pack Export MVP (triển khai module tạo và xuất file task pack có hash toàn vẹn/checksum SHA-256).
3. **AI-GW-A17B:** Result Import MVP (triển khai parser kiểm tra cấu trúc và tính toàn vẹn của report).
4. **AI-GW-A17C:** Workspace Chat export/import helper (tích hợp helper UI vào Workspace Chat).
5. **AI-GW-A17D:** Git observer / validation receipt / anti-fake hardening (triển khai các bộ so sánh observed evidence cục bộ với declared evidence).
6. **RM-SYNC-A17:** Master roadmap sync after A17 (đồng bộ và cập nhật trạng thái Phase 5 thành DONE hoàn toàn sau khi A17 hoàn tất).

> [!IMPORTANT]
>
> - `AI-GW-A17-DESIGN` là gate thiết kế tài liệu duy nhất. Các subgate tiếp theo chưa được mở và hoạt động implementation chưa bắt đầu.
> - Bất kỳ hoạt động sửa đổi mã nguồn (`src/`) hoặc kiểm thử (`tests/`) nào cho A17 đều bị nghiêm cấm trong gate này.
