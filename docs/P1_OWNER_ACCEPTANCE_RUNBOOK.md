# Sổ Tay Nghiệm Thu Của Chủ Sở Hữu Cho P1 (P1 Owner Acceptance Runbook)

Sổ tay hướng dẫn này dành riêng cho chủ sở hữu là con người. Chỉ một mình AI agent không thể tự hoàn thành tài liệu này.

## Mục Tiêu (Goal)

Kiểm chứng rằng AIOS WorkLens có thể hỗ trợ quy trình làm việc hằng ngày của chủ sở hữu mà không bắt buộc chủ sở hữu phải hiểu về các bài test hoặc chi tiết triển khai nội bộ.

## Các Chế Độ Dữ Liệu An Toàn (Safe Data Modes)

### Chế độ dữ liệu giả lập (Fake-data mode)

Sử dụng các vụ việc giả lập, tên tệp giả lập và chi tiết vận hành giả lập. Đây là chế độ an toàn nhất để chụp ảnh màn hình hoặc chia sẻ kết quả.

### Chế độ dữ liệu thực tế chỉ dùng cục bộ (Real-data local-only mode)

Nếu bạn sử dụng tài liệu của công ty hoặc tài liệu nhạy cảm, bắt buộc phải giữ chúng ở chế độ chỉ dùng cục bộ (local-only). Tuyệt đối không dán chúng vào NotebookLM, cloud chat, IDE bên ngoài hoặc ảnh chụp màn hình công khai.

## Các Bước Nghiệm Thu (Acceptance Steps)

1. Mở repository tại máy cục bộ.
2. Chạy hướng dẫn quy trình của chủ sở hữu:

   ```powershell
   $env:PYTHONPATH='src'; py -3 -m aios_habit.cli owner-workflow --fake-data
   ```

3. Đọc kỹ các bước được in ra từ trên xuống dưới.
4. Đối với dữ liệu giả lập, thực hiện tìm kiếm RAG, đánh giá bằng chứng, quyết định xuất prompt và quyết định dán câu trả lời ngược lại chỉ bằng nội dung giả lập.
5. Đối với dữ liệu thực tế, dừng lại trước bất kỳ bước xuất ra bên ngoài nào trừ khi bằng chứng được phân loại rõ ràng là `cloud_safe`.
6. Ghi nhận xem từng bước có dễ hiểu mà không cần phải đọc tệp test hay hỏi lại AI agent hay không.
7. Báo cáo kết quả lại cho ChatGPT bằng cách sử dụng mẫu bên dưới.

## Tiêu Chí Đạt (PASS Criteria)

- Bạn có thể dễ dàng xác định hành động tiếp theo từ hướng dẫn.
- Bạn hiểu rõ khi nào nhãn `local_only` sẽ chặn việc xuất dữ liệu ra bên ngoài.
- Bạn có thể nhận biết bằng chứng / trích dẫn nào hỗ trợ cho câu trả lời.
- Bạn biết phải làm gì khi bằng chứng chưa đầy đủ (insufficient evidence).
- Bạn có thể ghi nhận xem quy trình có chấp nhận được cho công việc hằng ngày hay không.

## Tiêu Chí Không Đạt (FAIL Criteria)

- Bạn phải cần đến AI agent để giải thích lệnh nào cần chạy tiếp theo.
- Bạn không thể phân biệt được liệu dữ liệu có bị gửi ra khỏi máy tính hay không.
- Bằng chứng / trích dẫn không rõ ràng, mơ hồ.
- Việc xuất prompt / dán ngược câu trả lời gây bối rối, khó hiểu.
- Quy trình tạo cảm giác quá nặng nề về mặt thủ công cho công việc hằng ngày.

## Những Gì Bị Coi Là "Quá Nặng Về Thủ Công" (Too Manual)

- Phải gõ nhiều hơn một lệnh không rõ ràng trước khi nhìn thấy hướng dẫn hữu ích.
- Phải soi mã nguồn kiểm thử Python mới hiểu được quy trình làm việc.
- Các bước sao chép / dán không giải thích rõ ràng các rủi ro về quyền riêng tư và bằng chứng.
- Không có câu trả lời rõ ràng khi gặp tình huống chưa đủ bằng chứng.

## Bằng Chứng An Toàn và Không An Toàn Khi Chia Sẻ

An toàn để chia sẻ:
- Ảnh chụp màn hình dùng dữ liệu giả lập.
- Ghi chú ĐẠT / KHÔNG ĐẠT (PASS/FAIL) không chứa tên công ty hoặc nội dung thô.
- Các thông báo lỗi đã được làm sạch (redacted).

Tuyệt đối không an toàn để chia sẻ:
- API key, token.
- Tệp `.env`.
- Tài liệu công ty / MOM / tài liệu nguồn gốc.
- Nội dung bên trong thư mục `local_cases`.
- Các gói prompt đã tạo chứa văn bản nhạy cảm.
- Câu trả lời dán ngược lại chứa dữ liệu công ty.

## Mẫu Báo Cáo Của Chủ Sở Hữu (Owner Report Template)

```text
AIOS Owner Acceptance Run
Mode: fake-data / real-data-local-only
Date:
Result: PASS / FAIL
Too manual: YES / NO
Most confusing step:
Privacy confidence: HIGH / MEDIUM / LOW
Evidence/citation confidence: HIGH / MEDIUM / LOW
Notes:
```

## Trạng Thái Hiện Tại (Current Status)

Nghiệm thu thực tế của chủ sở hữu ở trạng thái `BLOCKED_NEEDS_OWNER_ACCEPTANCE` cho đến khi chủ sở hữu là con người hoàn thành lượt chạy này và báo cáo kết quả.

