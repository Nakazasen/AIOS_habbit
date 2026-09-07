# ADR-0008: Runtime Agent kế thừa và mặt bàn Code-OSS

Status: `ACCEPTED`
Ngày quyết định: 2026-09-07
Vai trò chủ sở hữu: Project owner / Architecture reviewer
Xem xét lần cuối: 2026-09-07
Chu kỳ xem xét: Mỗi lần nâng phiên bản runtime hoặc thay đổi ranh giới quyền

## Bối cảnh

US6 đã có Task Pack, proposal, nhập kết quả và policy nền, nhưng chưa có session/tool lifecycle, worktree, terminal, checkpoint, resume và giao diện lập trình đủ dùng hằng ngày. Tự xây toàn bộ harness sẽ chậm, trùng chức năng và tạo thêm rủi ro quyền.

## Các phương án

1. Dùng Code-OSS + adapter OpenCode + governance AIOS.
2. Fork OpenCode desktop rồi đổi giao diện.
3. Tiếp tục mở rộng orchestrator hiện có thành một harness mới.

## Quyết định

Chọn phương án 1. OpenCode là runtime ứng viên chính qua server/adapter; Cline là benchmark và fallback nếu G1 chứng minh OpenCode không đáp ứng permission, session/resume hoặc event stream. Code-OSS là mặt bàn chuyên dụng cho `agent_work`; Workspace Chat vẫn là giao diện AIOS chính.

AIOS giữ Task Pack, policy, approval, receipt, Case/Evidence, privacy route và learning đã duyệt. Runtime giữ vòng model–tool, session, streaming, cancel/resume và MCP. Code-OSS giữ editor, diff, terminal, SCM, LSP và debugger. Không sao chép thương hiệu, icon, Marketplace hoặc thành phần phân phối độc quyền.

Bản đầu chỉ tự sửa trong Git worktree. Apply vào workspace thật cần đúng proposal digest đã duyệt. Không hỗ trợ tự commit, push, merge, deploy, quyền admin hoặc thao tác ngoài workspace.

## Hệ quả

- Ít mã tự viết hơn và có đường nâng upstream rõ.
- Cần adapter versioned, capability handshake và contract test chống drift.
- OpenCode thất bại G1 thì dừng, ghi blocker và spike Cline theo cùng rubric; không fork ngay.
- US5 có thể tái sử dụng harness sau G4 qua tool artifact bị giới hạn; US10 không được gọi coding tool.

## Bảo mật và quyền riêng tư

- AIOS là nguồn quyết định cuối; runtime deny mặc định.
- Không có đường từ RAG answer đến tool ghi.
- Approval bind task, session, base, payload, actor, scope, policy và expiry.
- Secret và `local_only` không vào provider hoặc hồ sơ thường; transcript/stdout thô không sao chép vào Case.
- Path traversal, symlink thoát root, command ngoài allowlist và approval replay phải bị chặn.

## Hoàn tác

Tắt feature flag, dừng adapter/extension và giữ US6 foundation hiện có. Không sửa lịch sử Git hoặc xóa dữ liệu người dùng. Runtime session có thể bị bỏ, nhưng receipt/digest đã ghi trong Case vẫn được bảo toàn.

## Bằng chứng

- [Đặc tả 009](../../specs/009-agent-harness-adoption/spec.md)
- [Kế hoạch 009](../../specs/009-agent-harness-adoption/plan.md)
- [Sổ LSU mục 30](../../Thảo_luận_AI_dự_đoán_lỗi_LSU.md#30-kế-hoạch-nâng-us6-thành-agent-lập-trình-và-thao-tác-file-đủ-dùng-hằng-ngày)
- [OpenCode server](https://opencode.ai/docs/server/), [OpenCode tools](https://opencode.ai/docs/tools/)
- [Cline checkpoints](https://docs.cline.bot/core-workflows/checkpoints), [Cline SDK](https://docs.cline.bot/sdk/architecture/overview)
- [Code-OSS](https://github.com/microsoft/vscode)
