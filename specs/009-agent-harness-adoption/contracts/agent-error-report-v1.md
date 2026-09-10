# Hợp đồng báo cáo lỗi Agent phiên bản 1

## 1. Mục đích

`aios_agent_error_report_v1` là payload duy nhất để persistence, Workspace Chat, Code-OSS và CLI trình bày lỗi của task Agent. Producer phải tạo báo cáo từ event/receipt quan sát được; UI không tự ghép raw exception và không đoán trạng thái.

## 2. Producer và thời điểm tạo

Gateway AIOS tạo report khi có một trong các điều kiện:

- runtime/adapter/probe thất bại;
- policy từ chối request/action;
- proposal/approval/base/digest hết hạn hoặc mismatch;
- command/test thất bại, timeout hoặc vượt budget;
- cancel/resume/rollback không xác minh sạch;
- persistence hoặc apply lỗi;
- dữ liệu bị redaction khiến không đủ bằng chứng kết luận.

Runtime/model chỉ cung cấp input tự khai. Adapter ánh xạ lỗi upstream sang reason code; Error Report Builder lấy observed fact và receipt để tạo payload cuối.

## 3. Schema logic

| Trường | Kiểu | Bắt buộc | Quy tắc |
|---|---|---|---|
| `schema_version` | chuỗi | có | cố định `aios_agent_error_report_v1` |
| `report_id` | chuỗi | có | duy nhất, không chứa path |
| `task_id` | chuỗi | có | khớp Task Pack |
| `session_id` | chuỗi/null | có | null nếu probe chưa tạo session |
| `status` | chuỗi | có | `failed`, `blocked`, `interrupted`, `cancelled`, `cancelled_with_residue` |
| `failed_step` | chuỗi | có | bước canonical, không lấy nguyên văn từ model |
| `reason_code` | chuỗi | có | mã nội bộ allowlist |
| `message_vi` | chuỗi | có | một câu tiếng Việt dễ hiểu, không raw error |
| `impact_vi` | chuỗi | có | nêu file/workspace có đổi hay không bằng dữ kiện quan sát |
| `next_actions_vi` | mảng chuỗi | có | 1–3 bước người dùng có thể làm tiếp |
| `observed_facts` | mảng object | có | chỉ fact đã làm sạch, có source và digest khi phù hợp |
| `receipt_refs` | mảng chuỗi | có | ID receipt, không phải absolute path |
| `can_resume` | boolean | có | chỉ true sau reconcile |
| `rollback_state` | chuỗi | có | `not_needed`, `available`, `completed`, `failed`, `unknown` |
| `redaction_summary` | object | có | số trường bị bỏ/cắt và reason code; không chứa nội dung đã bỏ |
| `created_at` | thời gian UTC | có | ISO 8601 |
| `report_digest` | chuỗi | có | SHA-256 trên payload không gồm chính field này |

### `observed_facts`

Mỗi phần tử gồm:

- `fact_kind`: `runtime_state`, `process_state`, `command_exit`, `workspace_state`, `digest_check`, `policy_decision`, `persistence_state`.
- `source`: `aios`, `adapter`, `verifier`, `git`.
- `status`: `ok`, `failed`, `unknown`, `redacted`.
- `safe_summary_vi`: câu tiếng Việt đã làm sạch.
- `evidence_digest`: SHA-256 hoặc null.
- `observed_at`: thời gian UTC.

## 4. Mã bước và reason code

### Bước

`probe`, `session_create`, `planning`, `editing`, `command`, `verification`, `approval`, `apply`, `rollback`, `cancel`, `resume`, `persistence`, `ui_delivery`.

### Reason code tối thiểu

- `RUNTIME_CAPABILITY_MISSING`
- `RUNTIME_CONNECTION_LOST`
- `RUNTIME_VERSION_MISMATCH`
- `POLICY_DENIED`
- `PATH_OUTSIDE_WORKTREE`
- `COMMAND_NOT_ALLOWED`
- `BASELINE_CHANGED`
- `PROPOSAL_MISMATCH`
- `APPROVAL_EXPIRED`
- `APPROVAL_REPLAYED`
- `VERIFICATION_FAILED`
- `VERIFICATION_INCOMPLETE`
- `COMMAND_TIMEOUT`
- `OUTPUT_BUDGET_EXCEEDED`
- `CANCEL_RESIDUE_DETECTED`
- `ROLLBACK_FAILED`
- `PERSISTENCE_FAILED`
- `PRIVACY_REDACTION_REQUIRED`
- `UNKNOWN_FAILURE`

Mã chưa biết phải map `UNKNOWN_FAILURE`; không đưa tên exception upstream ra UI.

## 5. Quy tắc ngôn ngữ và redaction

- `message_vi`, `impact_vi`, `next_actions_vi` và `safe_summary_vi` chỉ dùng tiếng Việt dễ hiểu.
- Được giữ token file/module/command/reason code khi cần đối chiếu, nhưng phải có giải thích tiếng Việt gần đó.
- Cấm raw exception, traceback, absolute path, username OS, hostname, secret, environment dump, prompt, transcript và raw stdout/stderr.
- Relative path chỉ hiển thị nếu thuộc allowed scope và đã qua safe-path validation.
- Chuỗi upstream không rõ ngôn ngữ hoặc chứa dữ liệu chưa phân loại phải bị thay bằng câu tổng quát tiếng Việt và reason code.
- UI không dùng `st.success` hoặc trạng thái thành công cho report có `status` khác success; contract này không có success state.

## 6. Persistence

- SQLite lưu toàn bộ payload đã làm sạch, `report_digest` và liên kết receipt theo record append-only.
- Raw error/output nếu cần điều tra chỉ nằm trong spool `local_only`, có locator/digest/retention riêng và không được UI thường phân giải.
- Ghi report và receipt liên quan phải atomic hoặc có recovery marker; không tạo report trỏ receipt chưa tồn tại mà không đánh dấu `persistence_state=unknown`.
- Cùng idempotency key/cùng digest trả record cũ; cùng key/khác digest bị từ chối.

## 7. Hợp đồng UI

Mỗi client phải hiển thị tối thiểu:

1. `message_vi`.
2. `impact_vi`, đặc biệt “workspace thật chưa thay đổi” hoặc trạng thái `unknown`.
3. Các bước trong `next_actions_vi`.
4. Khả năng tiếp tục (`can_resume`) và trạng thái rollback.
5. Mã đối chiếu `report_id`; reason code nằm trong phần chi tiết.

Không client nào tự đổi `failed`, `blocked`, `interrupted` hoặc `cancelled_with_residue` thành “đã hoàn tất”.

## 8. Ví dụ hợp lệ

```json
{
  "schema_version": "aios_agent_error_report_v1",
  "report_id": "ERR-TASK-009-001",
  "task_id": "TASK-009-001",
  "session_id": "SESSION-009-001",
  "status": "failed",
  "failed_step": "verification",
  "reason_code": "VERIFICATION_FAILED",
  "message_vi": "Kiểm thử bắt buộc chưa đạt nên thay đổi chưa được áp dụng.",
  "impact_vi": "Workspace thật chưa thay đổi; bản đề xuất vẫn nằm trong vùng làm việc tách biệt.",
  "next_actions_vi": [
    "Mở phần kiểm thử để xem tên bước chưa đạt.",
    "Yêu cầu Agent sửa lỗi trong cùng phạm vi rồi tạo đề xuất mới."
  ],
  "observed_facts": [
    {
      "fact_kind": "command_exit",
      "source": "verifier",
      "status": "failed",
      "safe_summary_vi": "Một lệnh kiểm thử bắt buộc trả mã thoát khác 0.",
      "evidence_digest": "sha256:0123456789abcdef",
      "observed_at": "2026-09-10T00:00:00Z"
    }
  ],
  "receipt_refs": ["RCP-VERIFY-001"],
  "can_resume": true,
  "rollback_state": "not_needed",
  "redaction_summary": {"removed_fields": 2, "reason_codes": ["RAW_OUTPUT_OMITTED"]},
  "created_at": "2026-09-10T00:00:01Z",
  "report_digest": "sha256:fedcba9876543210"
}
```

## 9. Trường hợp bắt buộc kiểm thử

- Exception tiếng Anh có absolute path và secret được map sang tiếng Việt, không còn chuỗi cấm.
- Test exit code 1 tạo `VERIFICATION_FAILED`, UI không hiển thị thành công.
- Mất kết nối giữa write tạo `interrupted` với `can_resume=false` cho đến reconcile.
- Cancel còn process con tạo `cancelled_with_residue` và hướng dẫn xử lý.
- Proposal hết hạn/base đổi nêu rõ workspace chưa bị áp dụng.
- Ghi persistence lỗi không tạo receipt/report nửa vời.
- Report digest bị sửa phải bị từ chối khi đọc lại.
