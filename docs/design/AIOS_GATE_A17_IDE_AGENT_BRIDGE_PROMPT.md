# Gate AI-GW-A17-DESIGN — IDE Agent Bridge Design Prompt

Bạn là docs-only design executor cho repo `AIOS_habbit`.

## 1. Mục tiêu (Docs-Only Design Goal)

Thiết lập và hoàn thiện tài liệu kiến trúc, ranh giới an toàn, lược đồ truyền tin (Task Pack & Report Schemas) và mô hình chống gian lận cho cấu phần IDE Agent Bridge.

> [!IMPORTANT]
>
> - Đây là gate **chỉ thiết kế tài liệu** (docs-only design).
> - Nghiêm cấm sửa đổi bất kỳ tệp tin mã nguồn (`src/`) hoặc kiểm thử (`tests/`) nào.
> - Nghiêm cấm sửa đổi các tệp `ROADMAP.md`, `WORKLENS_MASTER_ROADMAP.md`, `CHANGELOG.md` trong phạm vi gate này.
> - Nghiêm cấm mở implementation subgate `AI-GW-A17A` hoặc bắt đầu viết mã.
> - Sau khi thiết kế tài liệu này đạt trạng thái PASS, việc mở subgate `AI-GW-A17A` để triển khai code bắt buộc phải trải qua một task roadmap sync riêng biệt tuân thủ cơ chế quản trị (governance).

---

## 2. Phạm vi Thiết kế (Design Scope)

### Thiết kế Task Pack (`aios_agent_task_pack_v1`)

Hỗ trợ xuất gói tác vụ JSON deterministic sử dụng hàm băm **SHA-256** (không dùng MD5 làm khóa toàn vẹn). Các trường bao gồm:

- Thông tin nhận diện và mục tiêu (`schema_version`, `task_id`, `task_type`, `gate`, `agent_class`, `objective`).
- baseline môi trường repo (`repo` chứa `logical_repo_id`, `repo_path_policy` không chứa absolute path thực tế khi truyền cloud, `expected_branch`, `expected_head`).
- phạm vi cho phép (`allowed_files`, `forbidden_files`, `allowed_commands`, `forbidden_commands`, `required_tests`).
- chính sách riêng tư (`privacy_class`, `destination`, `purpose`, `consent_ref`, `source_policy`).
- thông tin quản trị và rollback (`roadmap_reference`, `pass_fail_rules`, `rollback`, `required_report_fields`, `created_at`, `pack_sha256`).

### Thiết kế Report Import (`aios_agent_report_v1`)

Thiết lập bộ phân tích và đối chiếu bằng chứng bao gồm:

- Thông tin tự khai từ agent (`declared_status`, `baseline`, `final_state`, `declared_files`, `declared_commands`, `declared_tests`, `risks`, `blockers`, `rollback`, `reason_codes`, `report_sha256`).
- Thuật toán phân biệt rõ ràng **Declared Evidence** (tự khai) và **Observed Evidence** (kiểm chứng độc lập qua môi trường đĩa local).
- Phán quyết verdict hữu hạn: `VERIFIED_PASS`, `FAIL`, `REVIEW_REQUIRED`, `INVALID_REPORT` kết hợp với các lý do cụ thể trong `reason_codes[]`.
- Không tự động phong `VERIFIED_PASS` hoặc tự động tạo confirmed memory khi thiếu bằng chứng thực tế quan sát được.

---

## 3. Các Chốt Chặn Bảo Mật (Import Safety Controls)

- Cấm path traversal (`../`) và theo dõi symlink độc hại để thoát khỏi thư mục dự án.
- Cô lập lưu trữ cục bộ tại `local_runs/agent_bridge/{outbox,inbox,processed}` (bị Git ignore).
- Giới hạn kích thước file và độ sâu của JSON parser.
- UTF-8 strict và không sửa mojibake tự động im lặng.
- Ghi đè file nguyên tử (atomic writes).

---

## 4. Kế Hoạch Subgate Thống Nhất (Unified Subgate Plan)

Kiến trúc IDE Agent Bridge được triển khai theo các giai đoạn tuần tự sau:

1. **AI-GW-A17-DESIGN:** Docs-only design (thiết kế tài liệu - gate hiện tại).
2. **AI-GW-A17A:** Task Pack Export MVP (tạo file task pack có hash toàn vẹn/checksum SHA-256).
3. **AI-GW-A17B:** Result Import MVP (parser và kiểm tra tính toàn vẹn của report).
4. **AI-GW-A17C:** Workspace Chat export/import helper (tích hợp helper UI).
5. **AI-GW-A17D:** Git observer / validation receipt / anti-fake hardening (xác minh observed evidence cục bộ).
6. **RM-SYNC-A17:** Master roadmap sync after A17 (đồng bộ và mở Phase 5 thành DONE).

---

## 5. Các Lệnh Xác Minh Tài Liệu (Design Validation Commands)

Chạy kiểm tra tình trạng Git và linter của các tài liệu:

```powershell
git diff --name-only
git diff --stat
git diff --check
git status --short
```

Không thực hiện commit hoặc push lên origin nếu các bước kiểm tra diff hoặc mojibake báo lỗi.

---

## 6. Định Dạng Kết Quả Đầu Ra (Output Format Template)

Báo cáo kết quả phải sử dụng đúng mẫu cấu trúc dưới đây để điền thông tin sau khi kiểm tra. Chỉ được điền PASS khi có bằng chứng (evidence) rõ ràng, nếu không có đủ bằng chứng, trạng thái bắt buộc phải là FAIL hoặc REVIEW_REQUIRED. Không được mặc định điền `RISKS: none`; nếu không phát hiện rủi ro nào sau khi chạy các bước kiểm tra, phải ghi rõ `none observed after checks` kèm danh sách cụ thể các bước kiểm tra đã thực hiện.

```text
FINAL_STATUS:
- PASS_A17_DESIGN_DOCS_READY_FOR_AUDIT
hoặc
- FAIL_PRECONDITION
hoặc
- FAIL_SCOPE
hoặc
- FAIL_VALIDATION
hoặc
- FAIL_NEEDS_FIX

AUDIT_RESULT:
- PASS_WITH_EVIDENCE
hoặc
- FAIL_WITH_BLOCKERS

BASELINE: [sha256/git hash of base commit]
TASK_PACK_SCHEMA: aios_agent_task_pack_v1
REPORT_IMPORT_SCHEMA: aios_agent_report_v1

FAKE_PASS_DETECTION:
- PASS_WITH_EVIDENCE
hoặc
- FAIL_WITH_BLOCKERS
hoặc
- REVIEW_REQUIRED

FILES_CHANGED:
- observed_files:

TESTS: N/A (docs-only design gate, verification via docs checking)

AUDIT_STATUS:

FORBIDDEN_DIRTY:

COMMIT_CREATED:
- YES_WITH_HASH:
hoặc
- NO_WITH_REASON:

PUSH_PERFORMED: NO

RISKS:
- blockers:
- high:
- medium:
- low:

NEXT_STEP: Đợi Codex Design Audit phê duyệt bản cập nhật thiết kế
```
