# Đặc tả: Agent lập trình và thao tác file có kiểm soát

**Mã tính năng**: `009-agent-harness-adoption`
**Nhánh lập kế hoạch**: `gate1-local-case-sqlite`
**Ngày tạo**: 2026-09-07
**Trạng thái**: `READY_FOR_TASK_EXECUTION`

## 1. Mục tiêu

Nâng nền US6 hiện có thành trợ lý lập trình đủ dùng hằng ngày mà không tự viết lại editor, terminal hoặc vòng lặp agent đã có ở các dự án trưởng thành. AIOS giữ quyền, bằng chứng, phê duyệt và dữ liệu; runtime kế thừa đảm nhiệm phiên agent và tool; Code-OSS là mặt bàn chuyên dụng. Workspace Chat vẫn là giao diện AIOS chính.

## 2. Hành trình người dùng và kiểm thử

### US1 — Xác minh runtime kế thừa ở chế độ chỉ đọc (P1)

Kỹ sư chọn một repo fixture và yêu cầu Agent đọc, tìm kiếm, lập kế hoạch. Hệ thống phải tạo hoặc tiếp tục phiên, truyền sự kiện và từ chối mọi thao tác ghi khi policy cấm.

**Kiểm thử độc lập**: khởi động runtime đã pin phiên bản, chạy health/capability probe, đọc và tìm đúng file; thử edit/command bị từ chối và không có file đổi.

**Tiêu chí chấp nhận**:

1. Khi runtime tương thích, health, version, session, event stream, read/search và permission probe đều có receipt.
2. Khi runtime không chặn được write/command hoặc không resume được bằng ID ổn định, G1 dừng và ghi `BLOCKED`; không vá sâu hoặc fork ngay.

### US2 — Hoàn tất một task lập trình trong worktree tách biệt (P2)

Kỹ sư duyệt Task Pack một lần, Agent sửa nhiều file và chạy lệnh trong ngân sách. Main workspace không đổi trước khi người dùng duyệt đúng diff; kết quả test phải do verifier quan sát độc lập.

**Kiểm thử độc lập**: sửa một bug fixture, tạo proposal bất biến, chạy test lỗi rồi sửa đạt, duyệt một phần diff, áp dụng và kiểm tra lại; rollback phải đưa worktree về trạng thái sạch.

**Tiêu chí chấp nhận**:

1. Write, rename, delete và command chỉ xảy ra trong worktree và phạm vi được duyệt.
2. Base commit, file hoặc proposal đổi sau duyệt thì apply phải từ chối và yêu cầu proposal mới.
3. Dừng hoặc restart không lặp lại thao tác đã hoàn tất và không để tiến trình con chạy sót.

### US3 — Sử dụng hằng ngày với bằng chứng AIOS (P3)

Kỹ sư theo dõi task, quyền, diff, terminal và resume trong Code-OSS; từ Workspace Chat có thể mở hoặc tra cứu hồ sơ `agent_work`. Mọi kết quả được gắn receipt, còn bài học chỉ được tạo từ thay đổi đã duyệt và kiểm chứng.

**Kiểm thử độc lập**: hoàn tất một task qua Code-OSS và một task headless qua cùng protocol; đóng/mở lại ứng dụng, xem đúng trạng thái và bằng chứng mà không chỉnh JSON thủ công.

**Tiêu chí chấp nhận**:

1. Code-OSS và CLI/headless dùng cùng contract và cùng quyết định quyền.
2. Secret, dữ liệu `local_only`, transcript và stdout thô không xuất hiện trong hồ sơ hoặc giao diện thường.
3. Kết quả bị từ chối hoặc chưa kiểm chứng không được promotion thành bài học.

## 3. Trường hợp biên bắt buộc

- Workspace bẩn sẵn, file đích đổi sau proposal, path traversal và symlink thoát root.
- Đường dẫn Windows có khoảng trắng hoặc tiếng Việt; output UTF-8 không mojibake.
- Lệnh dài bị hủy, runtime mất kết nối, UI dừng giữa task và resume sau restart.
- Prompt injection trong file, secret trong môi trường/stdout và MCP ngoài allowlist.
- Người dùng từ chối một hunk, từ chối toàn bộ hoặc hủy task.

## 4. Yêu cầu chức năng

- **FR-001**: AIOS phải là nguồn quyết định cuối cho quyền, privacy và phê duyệt.
- **FR-002**: Runtime phải được pin phiên bản và vượt capability probe trước khi bật ghi.
- **FR-003**: Task Pack phải khóa workspace, base commit, file, lệnh, budget, privacy và tiêu chí đạt.
- **FR-004**: Mọi thao tác ghi phải diễn ra trong Git worktree tách biệt ở bản đầu.
- **FR-005**: Proposal phải bất biến và gắn digest, actor, scope, policy version cùng thời hạn.
- **FR-006**: Apply phải fail-closed khi workspace hoặc proposal đã đổi.
- **FR-007**: Lệnh chỉ chạy từ allowlist; command ngoài danh sách cần proposal mới hoặc bị từ chối.
- **FR-008**: Event và receipt phải append-only, đọc lại được và chống ghi lặp.
- **FR-009**: Verifier phải dựa trên exit code và trạng thái workspace quan sát được, không tin lời model.
- **FR-010**: Phiên phải cancel/resume an toàn sau khi UI hoặc runtime restart.
- **FR-011**: Code-OSS và CLI/headless phải dùng cùng protocol; Workspace Chat chỉ mở và tra cứu hồ sơ.
- **FR-012**: Không hỗ trợ tự commit, push, merge, deploy, quyền admin hoặc thao tác ngoài workspace ở bản đầu.
- **FR-013**: Không thêm cơ sở dữ liệu riêng cho transcript/session runtime.
- **FR-014**: Không gửi dữ liệu `local_only` hoặc secret sang provider/runtime không được phép.
- **FR-015**: Cline chỉ là chuẩn đối chiếu và fallback sau khi OpenCode không đạt G1 bằng bằng chứng.

## 5. Thực thể chính

- **AgentTaskPack**: nhiệm vụ và toàn bộ ranh giới được phép.
- **RuntimeSessionBinding**: ánh xạ task với phiên runtime đã pin và trạng thái resume.
- **ActionProposal**: diff hoặc command bất biến đang chờ quyết định.
- **ExecutionReceipt**: sự kiện, digest trước/sau, lệnh, exit code, test và checkpoint.
- **AgentWorkRecord**: siêu dữ liệu và liên kết bằng chứng trong hồ sơ AIOS; không chứa transcript thô.

## 6. Tiêu chí thành công đo được

- **SC-001**: Đạt 12/12 tình huống an toàn và vòng đời tại mục 30.9 của sổ LSU.
- **SC-002**: Hoàn thành ít nhất 8/10 task benchmark cố định và không thấp hơn baseline OpenCode tốt nhất quá một task khi cùng model, thời gian và quyền.
- **SC-003**: 100% tình huống permission, privacy, resume, rollback và observed evidence đạt; không bù bằng điểm trung bình.
- **SC-004**: Không có write/command ngoài proposal đã duyệt và không có PASS chỉ dựa trên lời model.
- **SC-005**: Người dùng hoàn tất task hằng ngày bằng Code-OSS hoặc CLI mà không sửa JSON thủ công.
- **SC-006**: Clean-machine Windows E2E và toàn bộ quality gate AIOS đạt trước khi tuyên bố đủ dùng hằng ngày.

## 7. Giả định và ranh giới

- Một người dùng cục bộ; actor do app context cấp, không lấy từ prompt hay biểu mẫu tự khai.
- OpenCode là ứng viên chính cho G1; phiên bản cụ thể chỉ được khóa sau probe.
- Code-OSS cung cấp editor, terminal, SCM, LSP và debugger; không dùng tài sản thương hiệu hoặc Marketplace độc quyền.
- Không mở swarm, scheduler nhiều máy, điều khiển thiết bị hoặc tích hợp dữ liệu nhà máy trong feature này.
- US5, US10 và US11 không phải điều kiện chặn G1; mỗi miền vẫn giữ quyền riêng.
