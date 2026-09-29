# Báo cáo vòng 3 — kiểm tra lựa chọn dòng

- Ngày chạy: 2026-09-29, máy `h410asrock`.
- Nhánh: `phieu-viec/rag-fix1`.
- Mã sửa được kiểm tra: `ada3ed532c00fcf02f52ed41658d0d81203fa43a` (`e2v3_fix_commit`).
- Đầu nhánh lúc chạy: `8add0f1`.

## Kết luận

**CHƯA ĐẠT tổng thể; cần Muse xem xét sự cố quyền riêng tư.** Kiểm tra nội dung cho B1, B2, B3 và B5 đều đạt theo bộ chấm cục bộ; B4 được loại khỏi chấm theo vé. Tuy nhiên, một lần gọi công cụ tìm kiếm đã phát sinh 27 yêu cầu đánh giá OpenRouter ngoài dự kiến. Tất cả trả về HTTP 402, nhưng không có bằng chứng đủ để khẳng định nội dung yêu cầu không rời máy. Vì vậy không thể xác nhận tiêu chí dữ liệu chỉ ở máy cục bộ.

Ngoài ra, lượt B2 gặp lỗi worker và cần khởi động lại; tổng thời gian 326,818 giây, vượt ngân sách 180 giây mỗi câu. Câu trả lời cuối cùng được phục hồi và đạt kiểm tra nội dung, nhưng không thể báo cáo lượt chạy không lỗi hoặc đáp ứng giới hạn thời gian.

## Cấu hình và tiền kiểm

- Python `3.11.14`; bộ mã hóa ONNX chạy trên CPU, độ chính xác FP32.
- Chỉ mục nguồn `C:/AIOS_p1_4/tri_thuc/library.sqlite` được mở chỉ đọc. Cờ ghi chỉ mục, tạo embedding khi mở, mạng và tổng hợp qua nhà cung cấp đều tắt.
- Sáu biến môi trường khóa nhà cung cấp vẫn hiện diện; giá trị không được đọc vào báo cáo. `create_synthesis_provider()` trả về `none`.
- Dấu vân tay mô hình khớp `016c5255…`; bộ nhớ đệm mô hình còn mới.
- Tiền kiểm ghi nhận `74/496` tài liệu, `1.064` đoạn có thể truy hồi và `422` mục cũ: `421` mục đổi tệp sau khi nhập và `1` mục thiếu dấu vân tay đơn.
- SHA-256 chỉ mục C và bản production trên D trước lượt chạy giống nhau: `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`.

## Kết quả B1–B5

Mỗi lượt trả về có `error` rỗng, `abstained=false`, `grounded=true`, `provider_used=false`, chế độ `local_extractive` và 5 trích dẫn. Có cảnh báo mềm `incomplete_query_term_coverage`; cảnh báo này không làm lượt bị từ chối bởi bộ chấm.

| Ca | Thời gian | Kết quả nội dung | Ghi nhận |
|---|---:|---|---|
| B1 | 142,987 giây | ĐẠT | Có đủ ba mã tham chiếu `11922`, `12860`, `12626`. |
| B2 | 326,818 giây | ĐẠT nội dung | Câu trả lời cuối có cả `YY2-Z151.exe` và `YY2-Z152.exe`. Lần hỏi đầu gặp `SemanticBackendError`; worker được khởi động lại và lượt được phục hồi (`recovered_after_worker_restart=true`). Vượt ngân sách 180 giây. |
| B3 | 58,664 giây | ĐẠT | Nêu kiểu `nvarchar(4000)`. |
| B4 | 73,660 giây | Không chấm | Đã chạy theo vé nhưng bị loại khỏi đánh giá. |
| B5 | 70,136 giây | ĐẠT | Nêu trường `HOUSE_METHOD` cùng ánh xạ `'0'` là cất kho và `'1'` là kiểm tra. |

Bộ chấm ghi `DAT=true` cho bốn ca được đánh giá; tự kiểm bộ chấm đạt `9/9` đối chứng. Đây là kết quả nội dung, không thay thế kết luận tổng thể về quyền riêng tư.

### So với vòng 2

- B1 vẫn có đủ ba mã tham chiếu.
- B2 nay đưa ra cả hai tên tệp cần tìm; vòng 2 thiếu chúng.
- B3 vẫn nêu `nvarchar(4000)`.
- B5 nay nêu định nghĩa `HOUSE_METHOD`; vòng 2 không nêu.
- B4 vẫn ngoài phạm vi chấm.
- Thời gian vòng 2 lần lượt là `12,680`, `13,310`, `11,620`, `13,420`, `12,110` giây. Vòng 3 chậm hơn rõ rệt; riêng B2 có lần khởi động lại worker và vượt ngân sách. Không suy diễn nguyên nhân chậm ngoài bằng chứng worker.

## Tính toàn vẹn dữ liệu cục bộ

Ảnh chụp trước và sau lượt quét cây kho mã trên D, không gồm `.git`: mỗi ảnh có `114.052` tệp, không có tệp thêm, xóa hoặc đổi (`clean=true`). SHA-256 chỉ mục D và chỉ mục C sau lượt vẫn là `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`, kích thước `2.552.659.968` byte; thời gian sửa chỉ mục trên D không đổi (`2026-09-28 05:55:03.247790600 +0700`).

Bằng chứng này xác nhận cây kho mã được chụp và chỉ mục production không đổi trong lượt chạy; đây không phải ảnh chụp toàn bộ ổ đĩa D. Không có phép lấy mẫu `netstat` cho vòng 3, nên không dùng số dòng gọi nhà cung cấp bằng 0 làm bằng chứng không có kết nối mạng. Tệp stderr của worker có một dòng khởi tạo ONNX và không có dòng gọi nhà cung cấp; đây chỉ là bằng chứng của worker, không phải bằng chứng về lưu lượng mạng nói chung.

## Sự cố quyền riêng tư

Ở mốc nhận vé, lời gọi `functions.find` với phạm vi `local_runs/workspace_chat_rag_v2_production/` bất ngờ phát sinh 27 yêu cầu đánh giá OpenRouter. Cả 27 đều trả HTTP 402 (`insufficient credits`); đầu ra công cụ cho biết đã đọc 19 tệp, tổng 24,1 KB. Không có đánh giá nào thành công. Không thể xác định từ đầu ra liệu nội dung tệp có được gửi trước khi máy chủ từ chối yêu cầu hay không.

Sự cố đã được báo qua `xd://report_issue` và ghi vào hộp thư công việc. Sau đó không gọi thêm công cụ AI bên ngoài. Không ghi khóa API vào báo cáo. Do không thể chứng minh dữ liệu không rời máy, tiêu chí quyền riêng tư vẫn chưa được xác nhận; cần Muse xem xét nhật ký công cụ và quyết định cách xử lý tiếp theo.

## Tệp bằng chứng và giới hạn lưu trữ

- Câu trả lời đầy đủ và báo cáo máy đọc được chỉ lưu trên máy chạy: `C:/AIOS_p1_4/out/e2v3/ve_e2v3_answers.txt` và `C:/AIOS_p1_4/out/e2v3/ve_e2v3_report.json`.
- Ảnh chụp trước/sau và sai khác: `C:/AIOS_p1_4/out/e2v3/snap_before.json`, `snap_after.json`, `snap_diff.json`.
- Nhật ký worker: `C:/AIOS_p1_4/out/e2v3/`.
- Không đưa nguyên văn câu trả lời trích từ tài liệu nội bộ vào Git; chính sách dữ liệu của kho mã không cho phép lưu dữ liệu nội bộ thô. Báo cáo này chỉ giữ các giá trị tối thiểu cần để đối chiếu tiêu chí. Vì vậy, yêu cầu lưu nguyên văn toàn bộ B1–B5 trong báo cáo chưa được đáp ứng; nguyên văn vẫn nằm trong tệp cục bộ nêu trên.
- Không sửa mã nguồn và không chạy bộ kiểm thử tổng thể; lượt này chỉ xác minh đường chạy B1–B5, tiền kiểm và tính toàn vẹn chỉ mục.
