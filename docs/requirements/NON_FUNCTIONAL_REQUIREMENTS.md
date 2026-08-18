# Đường Cơ Sở Yêu Cầu Phi Chức Năng (Non-functional Requirements Baseline)

Status: `PARTIAL`
Owner role: Project owner / architecture and release reviewer
Last reviewed: 2026-07-25
Review cadence: Before release or a material runtime boundary change

| ID | Danh mục | Yêu cầu | Trạng thái | Bằng chứng / Khoảng cách |
|---|---|---|---|---|
| NFR-01 | Quyền riêng tư | Mặc định ưu tiên cục bộ; tuyến dữ liệu ra bên ngoài cần đáp ứng đủ điều kiện chính sách. | `PARTIAL` | Chính sách Gateway đã triển khai cho luồng tiền kiểm / mock; tuyến provider thực tế có chốt chặn nhãn/đồng ý riêng và cần bằng chứng làm sạch/hợp nhất P0. |
| NFR-02 | Bảo mật | Thông tin xác thực / dữ liệu runtime riêng tư tuyệt đối không được theo dõi hoặc làm lộ bởi các chẩn đoán thông thường. | `PARTIAL` | Các chốt chặn gitignore/audit; giới hạn quét heuristic vẫn tồn tại |
| NFR-03 | Độ tin cậy | Sự cố ngừng hoạt động của provider không ngăn cản việc sử dụng cục bộ. | `PARTIAL` | Lỗi adapter được xử lý an toàn; chưa có chỉ tiêu cam kết tính khả dụng |
| NFR-04 | Khôi phục | Người vận hành có thể sao lưu/phục hồi trạng thái cục bộ được hỗ trợ kèm kiểm chứng. | `PARTIAL` | Cuộc diễn tập phục hồi tổng hợp ngày 25-07-2026 đã đạt cho 6 danh mục JSONL và 1 chỉ mục/tìm kiếm SQLite; RTO/RPO, dữ liệu thật và phục hồi xuyên phiên bản chưa được chứng minh. |
| NFR-05 | Hiệu năng | Hiệu năng truy xuất và nạp dữ liệu được đo lường trước khi công bố phát hành ra bên ngoài. | `PLANNED` | Chỉ có giao thức đo chuẩn (benchmark); hiện chưa có ngưỡng định lượng |
| NFR-06 | Tính tương thích | Ma trận hỗ trợ được công bố rõ ràng và kiểm chứng trước khi phát hành. | `PROPOSED` | Ma trận Windows/Python đang chờ chủ sở hữu phê duyệt |
| NFR-07 | Khả năng tiếp cận | Giao diện hỗ trợ có tài liệu nghiệm thu về bàn phím/tiêu điểm/trạng thái lỗi. | `PROPOSED` | Đã thiết lập checklist; cần đánh giá thủ công |
| NFR-08 | Khả năng quan sát | Chẩn đoán an toàn về quyền riêng tư và không yêu cầu gửi dữ liệu đo từ xa (telemetry). | `PROPOSED` | Cần quy trình cục bộ / danh mục log |
| NFR-09 | Khả năng bảo trì | Các quyết định trọng yếu, giao diện và bằng chứng phát hành có thể truy xuất nguồn gốc. | `ACTIVE` | ADRs / hợp đồng / cổng chất lượng |

## Quy Tắc Đo Lường (Measurement Rule)

Các giá trị độ trễ (latency), dung lượng (capacity), RTO/RPO và tính khả dụng (availability) chưa được đo lường cụ thể phải giữ ở trạng thái `TBD`. Tuyệt đối không được mô tả chúng như những cam kết ở cấp độ production.

## Các Bản Ghi Liên Quan (Related Records)

- [Đường cơ sở hiệu năng và dung lượng (Performance capacity baseline)](../operations/PERFORMANCE_CAPACITY_BASELINE.md)
- [Các phiên bản được hỗ trợ (Supported versions)](../release/SUPPORTED_VERSIONS.md)
- [Nghiệm thu khả năng tiếp cận (Accessibility acceptance)](../quality/UX_ACCESSIBILITY_ACCEPTANCE.md)

