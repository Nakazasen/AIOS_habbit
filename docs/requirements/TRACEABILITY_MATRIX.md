# Ma Trận Truy Xuất Nguồn Gốc (Traceability Matrix)

Status: `ACTIVE`
Owner role: Project owner / quality reviewer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card closure and release candidate

| Yêu cầu | Quyết định / Thiết kế | Thành phần | Kiểm thử / Bằng chứng | Runbook / Kiểm soát phát hành |
|---|---|---|---|---|
| PR-01 | ADR-0002, sơ đồ container kiến trúc | `workspace_chat_app` | Cổng import Workspace Chat | Cài đặt / Hướng dẫn người dùng |
| PR-03/04 | ADR-0004, tuần tự tiền kiểm đám mây | `brain_gateway` | Kiểm thử Gateway/mock router | Đánh giá quyền riêng tư / ứng phó sự cố |
| PR-06 | ADR-0005, tuần tự gọi router | `workspace_chat_router_adapter` | Kiểm thử Workspace router / bằng chứng live smoke | Chính sách phụ thuộc / phát hành |
| PR-07 | ADR-0001, khung nhìn triển khai | Lưu trữ / truy xuất cục bộ | Toàn bộ kiểm thử / audit | Hướng dẫn sao lưu / phục hồi / vận hành |
| PR-08 | ADR-0002 | Trình khởi chạy / tuyến package | Kiểm thử ranh giới cũ | Danh mục dừng hoạt động (retirement) |
| NFR-02 | ADR-0006, mô hình mối đe dọa | `.gitignore`, audit | Kiểm thử CLI audit / fixture secret | Ứng phó sự cố |
| NFR-04 | ADR-0001/0003 | JSONL / SQLite cục bộ | Diễn tập phục hồi tổng hợp 25-07-2026: 6 loại thực thể JSONL + 1 đếm/tìm kiếm SQLite | Sao lưu / phục hồi |
| NFR-09 | Quản trị tài liệu | Trình kiểm tra docs / CI | `test_documentation_contract.py` | Checklist phát hành |

## Quy Tắc Duy Trì (Maintenance Rule)

Một liên kết bị thiếu trong ma trận này là một lỗ hổng về tài liệu/chất lượng, không phải bằng chứng cho thấy yêu cầu đó đã được đáp ứng. Các chốt chặn nằm trong kế hoạch vẫn giữ nguyên trạng thái cho đến khi bằng chứng được ghi nhận đầy đủ.

