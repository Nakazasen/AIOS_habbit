# Quy Tắc Kiểm Chứng (Validation Rules)

## Các Giá Trị Trạng Thái (Status Values)

- `PASS`: đạt đầy đủ tiêu chí, có bằng chứng (evidence) xác thực.
- `FAIL`: không đạt tiêu chí.
- `PARTIAL`: đạt một phần, cần bổ sung.
- `BLOCKED`: không thể hoàn thành do thiếu đầu vào / quyền hạn / bằng chứng.
- `NOT_APPLICABLE`: không áp dụng, cần ghi rõ lý do.

## Kiểm Chứng Bộ Nhớ (Memory Validation)

Bộ nhớ đạt `PASS` khi:

1. Có `memory_id` duy nhất.
2. Có `memory_type` hợp lệ.
3. Có nhận định (statement) ngắn gọn, không phải trích dẫn thô (raw quote) quá dài.
4. Có ít nhất một bản ghi bằng chứng (evidence record).
5. Có mức độ tin cậy (confidence).
6. Có ranh giới / phạm vi áp dụng (boundary/scope).
7. Tuyệt đối không chứa suy đoán chưa được gắn nhãn rõ ràng.
8. Có đường dẫn hoàn tác / dừng hoạt động (rollback/deprecation path).

## Kiểm Chứng Dự Án (Project Validation)

Thẻ dự án (Project card) đạt `PASS` khi:

1. Đường dẫn tồn tại hoặc có lý do xác đáng vì sao chưa xác minh.
2. Có mục đích rõ ràng (purpose).
3. Có trạng thái cụ thể (status).
4. Có tính liên quan đến bộ nhớ (memory relevance).
5. Có bằng chứng hoặc trạng thái ứng viên (candidate).

## Kiểm Chứng Quy Trình (Workflow Validation)

Quy trình làm việc (Workflow) đạt `PASS` khi có đầy đủ:

- Bộ kích hoạt (Trigger).
- Đầu vào (Inputs).
- Các bước thực hiện (Steps).
- Đầu ra (Outputs).
- Xác thực (Validation).
- Tiêu chí Đạt / Không đạt (PASS/FAIL criteria).
- Phương án hoàn tác (Rollback).
- Bàn giao (Handover).
- Bằng chứng (Evidence).

## Kiểm Chứng Giai Đoạn (Phase Validation)

Một giai đoạn đạt `PASS` khi:

- Các sản phẩm chuyển giao (deliverables) tồn tại đầy đủ.
- Phạm vi không bị vượt quá giới hạn đã định.
- Rủi ro được ghi nhận đầy đủ.
- Quá trình kiểm chứng hoàn thành thành công.
- Handover được cập nhật.
- Đường dẫn hoàn tác rõ ràng.
- Changelog được cập nhật.

