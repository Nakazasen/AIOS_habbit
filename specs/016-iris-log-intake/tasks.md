# Nhiệm vụ: Nhận log JIG Iris, ngưỡng thật và gửi email cảnh báo

**Đầu vào**: `specs/016-iris-log-intake/spec.md`.

**Điều kiện**: Dữ liệu thật gắn nhãn `local_only`, không vào Git hay prompt ngoài; kiểm thử chỉ dùng fixture tổng hợp.

**Kiểm thử**: Viết kiểm thử trước, bảo đảm thất bại trước khi sửa và đạt sau khi sửa.

## Giai đoạn 1: Bộ chuyển đổi log Iris (hạng mục 1 — kỳ hạn 23/09/2026)

- [ ] T016-01 Tạo `src/aios_habit/production_prediction/iris_log_adapter.py`: `doc_log_iris()`, tách ma trận rộng `<HỌ>:<MÀU>:<VỊ TRÍ>[<đơn vị>]`, bỏ canh `999`, giữ `RESULT:<MÀU>` làm `target_label`
- [ ] T016-02 Nối bộ chuyển đổi vào Thẻ 1 trong `src/aios_habit/prediction_shadow_ui.py`
- [ ] T016-03 Sửa `parse_jig_log_line` trong `jig_log_ingest.py` hiểu dòng Iris thật, kể cả khi dán kèm dòng tiêu đề
- [ ] T016-04 Liệt kê cột còn thiếu khi tệp không hợp lệ, bỏ câu thông báo chung chung

## Giai đoạn 2: Ngưỡng trên/dưới thật (hạng mục 2 — kỳ hạn 23/09/2026)

- [ ] T016-05 Tạo `metric_limits.py`: ngưỡng theo (JIG, chỉ số) kèm `gioi_han_tren`, `gioi_han_duoi`, `nguon`, `nguong_phan_tram`
- [ ] T016-06 Đọc ngưỡng từ tệp nhóm Spec/CamPos để tự điền
- [ ] T016-07 Dùng ngưỡng thật trong `evaluate_single_log_ewma` thay cho trung bình ± 3σ
- [ ] T016-08 Truyền `usl/lsl` thật vào `dung_du_lieu_bieu_do` để biểu đồ có đường giới hạn trên/dưới
- [ ] T016-09 Thêm đường nhập ngưỡng qua chat, có xem lại và xóa

## Giai đoạn 3: Gửi email cảnh báo (hạng mục 3)

- [ ] T016-10 Lưu cấu hình SMTP ngoài Git, không ghi mật khẩu vào mã nguồn
- [ ] T016-11 Nối `build_alert_email` và `send_via_smtp` vào giao diện qua thẻ đề xuất có mã duyệt
- [ ] T016-12 Dùng lại ảnh đang xem trước, không vẽ lại; áp dụng giãn cách chống spam
- [ ] T016-13 Lỗi gửi mail là câu tiếng Việt kèm bước xử lý

## Giai đoạn 4: Kiểm chứng và bàn giao

- [ ] T016-14 Fixture tổng hợp cho ba nhóm tệp Iris
- [ ] T016-15 Kiểm thử bộ chuyển đổi, ngưỡng và thư viện mail
- [ ] T016-16 Chạy `compileall`, `pytest -q`, `cli audit`, `import workspace_chat_app`
- [ ] T016-17 Kiểm toán độc lập trước khi kết luận đạt

## Phụ thuộc

- Giai đoạn 2 cần T016-01 xong để biết tên chỉ số chuẩn.
- Giai đoạn 3 cần T016-08 để có ảnh biểu đồ mang ngưỡng thật.
- T016-17 chạy sau cùng, độc lập với người thực thi.

## Ghi chú

- Đã xong trước khi lập kế hoạch: `.gitignore` cho phép fixture vào Git, gỡ 12 kiểm thử thất bại (`commit 71d9f26`).
- Chưa có máy chủ SMTP nội bộ: nếu chưa xác nhận được, dừng ở thẻ đề xuất, không gửi thật.
