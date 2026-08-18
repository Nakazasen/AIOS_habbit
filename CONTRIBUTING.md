# Hướng dẫn Đóng góp vào AIOS WorkLens (Contributing)

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Each release candidate and contributor workflow change

## Trước khi thay đổi mã nguồn hoặc tài liệu

1. Đọc kỹ `CONSTITUTION.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md` và Gate Card liên quan.
2. Đọc các bản ghi ADR, yêu cầu, hợp đồng (contract), mô hình mối đe dọa/quyền riêng tư và kiểm thử liên kết.
3. Giữ các thay đổi nằm trong danh sách cho phép (allowlist) của gate. Không bắt đầu một tính năng mới khi chưa có quyết định phê duyệt phạm vi rõ ràng.

## Quy tắc Quyền riêng tư & Dữ liệu

Tuyệt đối không commit hoặc dán vào issues/PRs: API key, giá trị `.env`, `local_cases/`, `local_runs/`, tài liệu thô, ảnh chụp màn hình, dữ liệu JSONL/SQLite riêng tư, prompt đầy đủ hoặc dữ liệu Authorization của nhà cung cấp. Luôn sử dụng dữ liệu fixture tổng hợp (synthetic) và log đã làm sạch (sanitized).

## Quy trình Thay đổi (Change Workflow)

- Giữ thay đổi nhỏ gọn và có thể truy xuất nguồn gốc đến yêu cầu/ADR/bằng chứng kiểm thử.
- Bổ sung các bài kiểm thử trọng điểm cho hành vi mới hoặc thay đổi.
- Cập nhật tài liệu canonical khi hành vi, route, hợp đồng hoặc rủi ro thay đổi.
- Bảo toàn nguyên tắc giao diện ưu tiên Tiếng Việt (Vietnamese-first) và hành vi xử lý lỗi an toàn.
- Không bỏ qua kiểm tra audit hoặc xóa bài kiểm thử thất bại để lấy kết quả "PASS" giả tạo.

## Yêu cầu Xác thực & Kiểm chứng

Chạy toàn bộ [các cổng chất lượng (quality gates)](docs/quality/QUALITY_GATES.md) trước khi review. Người duy trì (maintainer) bắt buộc phải kiểm tra git diff và git status để ngăn chặn các artifact riêng tư/runtime.

## Tiêu chí Review (Review Expectations)

Người đánh giá sẽ kiểm tra phạm vi, kiến trúc, quyền riêng tư/bảo mật, kiểm thử, tác động vận hành, phương án khôi phục (rollback) và bằng chứng tài liệu. Các tuyến provider mới, thay đổi dữ liệu bền vững (persistence), phụ thuộc mới và các tuyến UI công khai đều yêu cầu sự phê duyệt từ các vai trò được liệt kê trong [quyền sở hữu và phê duyệt](docs/governance/OWNERSHIP_AND_REVIEW.md).

