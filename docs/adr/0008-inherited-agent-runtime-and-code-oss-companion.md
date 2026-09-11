# ADR-0008: Runtime Agent kế thừa cho trợ lý thực thi công việc

Status: `ACCEPTED`
Ngày quyết định: 2026-09-07
Vai trò chủ sở hữu: Project owner / Architecture reviewer
Xem xét lần cuối: 2026-09-11
Chu kỳ xem xét: Mỗi lần nâng phiên bản runtime hoặc thay đổi ranh giới quyền

## Bối cảnh

US6 đã có Task Pack, nhập kết quả và policy nền, nhưng chưa có vòng đọc–sửa–test, checkpoint, resume và trải nghiệm giao việc đủ dùng hằng ngày. Nhu cầu thực tế không chỉ là sửa code: kỹ sư còn cần tạo file, tạo báo cáo lỗi có biểu đồ và rà soát thiết kế công đoạn dựa trên tài liệu nền. Tự xây toàn bộ harness hoặc IDE sẽ chậm, trùng chức năng và tạo thêm rủi ro quyền.

## Các phương án

1. Dùng Workspace Chat + adapter OpenCode + governance AIOS; Code-OSS chỉ là công cụ kỹ thuật tùy chọn.
2. Fork OpenCode desktop rồi đổi giao diện.
3. Tiếp tục mở rộng orchestrator hiện có thành một harness mới.

## Quyết định

Chọn phương án 1. OpenCode là runtime ứng viên chính qua server/adapter; Cline là fallback nếu G1 chứng minh OpenCode không đáp ứng vòng đọc–sửa–test–resume–undo hoặc không chặn được hành động ngoài vùng. Workspace Chat là giao diện chính; không xây extension Code-OSS riêng ở MVP.

AIOS giữ Task Pack, policy theo vùng, checkpoint, verifier, receipt, Case/Evidence, privacy route và learning đã duyệt. Runtime giữ vòng model–tool, session, streaming và cancel/resume. `antigravity_bridge.py` tiếp tục là tuyến nguồn AI của Workspace Chat; chỉ bridge NVIDIA lập trình cũ nằm trong phạm vi thay thế.

Bản đầu tự động cho phép đọc, tìm, tạo/sửa file và chạy test trong vùng nhiệm vụ có checkpoint. Mã nguồn chạy trong Git worktree; báo cáo và rà soát công đoạn ghi vào vùng bản nháp. Người dùng không duyệt từng tool call hoặc toàn bộ diff; họ xem kết quả tiếng Việt và có thể dùng hoặc hoàn tác. Không hỗ trợ tự commit, push, merge, deploy, quyền admin, thao tác ngoài workspace hoặc tự thay tài liệu công đoạn chính thức.

## Hệ quả

- Ít mã tự viết hơn và có đường nâng upstream rõ.
- Cần adapter mỏng, capability probe và contract test chống drift.
- OpenCode thất bại G1 thì dừng, ghi blocker và spike Cline theo cùng rubric; không fork ngay.
- Báo cáo lỗi có biểu đồ là lát cắt đầu tiên; rà soát thiết kế công đoạn và sửa mã dùng lại cùng policy/checkpoint.
- Hàng đợi chỉ khóa một writer theo workspace; chưa xây scheduler hay nền tảng đa Agent.

## Bảo mật và quyền riêng tư

- AIOS là nguồn quyết định cuối; runtime tự động duyệt action nằm trong grant và deny rõ action ngoài grant.
- RAG/evidence chỉ có thể tạo bản nháp qua orchestrator đã khóa nguồn, vùng ghi và privacy route; câu trả lời tự do không được gọi tool ghi trực tiếp.
- Grant bind task, session, workspace, action, command, privacy route, policy và expiry.
- Secret và `local_only` không vào provider hoặc hồ sơ thường; transcript/stdout thô không sao chép vào Case.
- Path traversal, symlink thoát root, command ngoài allowlist và approval replay phải bị chặn.

## Hoàn tác

Tắt feature flag, dừng adapter và giữ nền US6 hiện có. Worktree và bản nháp quay về checkpoint; không sửa lịch sử Git hoặc xóa thay đổi có trước của người dùng. Runtime session có thể bị bỏ, nhưng receipt/digest đã ghi trong Case vẫn được bảo toàn.

## Bằng chứng

- [Đặc tả 009](../../specs/009-agent-harness-adoption/spec.md)
- [Kế hoạch 009](../../specs/009-agent-harness-adoption/plan.md)
- [Sổ LSU mục 30](../../Thảo_luận_AI_dự_đoán_lỗi_LSU.md#30-kế-hoạch-nâng-us6-thành-agent-lập-trình-và-thao-tác-file-đủ-dùng-hằng-ngày)
- [OpenCode server](https://opencode.ai/docs/server/), [OpenCode tools](https://opencode.ai/docs/tools/)
- [Cline checkpoints](https://docs.cline.bot/core-workflows/checkpoints), [Cline SDK](https://docs.cline.bot/sdk/architecture/overview)
- [Code-OSS](https://github.com/microsoft/vscode)
