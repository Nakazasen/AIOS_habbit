# Nhật Ký Cổng Giai Đoạn (Phase Gate Log)

## Mục Đích (Purpose)

Ghi lại các quyết định mở / đóng từng giai đoạn (phase).

## Định Dạng (Format)

| Ngày | Giai đoạn | Cổng kiểm soát | Quyết định | Bằng chứng | Người đánh giá | Ghi chú |
|---|---|---|---|---|---|---|
| 2026-06-20 | Phase 0 | Mở (Open) | OPENED | Gói nền tảng được tạo | AI Orchestrator | Chờ người dùng đánh giá |

## Quy Tắc Cốt Lõi (Rules)

- Tuyệt đối không mở giai đoạn tiếp theo nếu giai đoạn hiện tại chưa đạt (PASS).
- Mọi quyết định bắt buộc phải có tệp bằng chứng (evidence file) liên kết.
- Nếu thực hiện hoàn tác (rollback), phải ghi rõ mục tiêu hoàn tác và lý do cụ thể.

