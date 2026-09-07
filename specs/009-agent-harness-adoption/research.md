# Nghiên cứu và quyết định

## Quyết định 1 — Dùng adapter trước, không fork

**Chọn**: OpenCode server là ứng viên chính cho G1. Tài liệu chính thức công bố server HTTP/OpenAPI, health/version, session, diff, permission response, file search/read và SSE event; đây là bề mặt đủ để làm capability probe trước khi viết tích hợp sâu.

**Lý do**: giảm lượng mã tự viết và giữ khả năng cập nhật upstream. Quyền OpenCode hỗ trợ `allow`, `ask`, `deny`, nhưng AIOS vẫn là nguồn quyết định cuối và phải chứng minh deny bằng negative test.

**Phương án khác**: fork OpenCode chỉ được xem xét sau khi adapter OpenCode và Cline đều thất bại theo cùng rubric.

Nguồn: [OpenCode server](https://opencode.ai/docs/server/), [OpenCode tools](https://opencode.ai/docs/tools/), [OpenCode license](https://github.com/anomalyco/opencode/blob/dev/LICENSE).

## Quyết định 2 — Cline là benchmark và fallback

**Chọn**: dùng checkpoint, approval và kiến trúc SDK của Cline làm chuẩn so sánh; chưa tích hợp đồng thời trong G1.

**Lý do**: Cline có checkpoint tách khỏi lịch sử Git chính và lớp runtime/tool approval rõ, phù hợp để đánh giá resume/rollback mà không biến AIOS thành fork thứ hai.

Nguồn: [Cline checkpoints](https://docs.cline.bot/core-workflows/checkpoints), [Cline SDK](https://docs.cline.bot/sdk/architecture/overview), [Cline license](https://github.com/cline/cline/blob/main/LICENSE).

## Quyết định 3 — Code-OSS là mặt bàn, không phải nguồn policy

**Chọn**: extension mỏng hiển thị task, event, diff, terminal và approval từ protocol AIOS. Không sao chép thương hiệu, icon, Marketplace hoặc thành phần phân phối độc quyền của Microsoft.

**Lý do**: Code-OSS đã có editor, SCM, terminal, LSP, debugger và extension host; tự xây lại các phần này trong Streamlit không tạo thêm giá trị.

Nguồn: [Code-OSS repository](https://github.com/microsoft/vscode), [khác biệt Code-OSS và Visual Studio Code](https://github.com/microsoft/vscode/wiki/Differences-between-the-repository-and-Visual-Studio-Code).

## Quyết định 4 — Không thêm kho session

OpenCode giữ session kỹ thuật trong vùng local runtime. AIOS chỉ lưu ID, digest, trạng thái và receipt cần audit trong kho Case canonical. Transcript và stdout thô không được sao chép vào hồ sơ.

## Điểm phải giải quyết bằng G1

- Phiên bản OpenCode cụ thể, checksum/gói cài và notices.
- Permission có thực sự chặn write/command trước tool execution hay không.
- Session ID, SSE ordering, cancel và resume có đủ ổn định để tạo receipt/idempotency.
- Hành vi Windows với path tiếng Việt, process tree và long-running command.
