# VÉ KHẨN: INDEX-HASH-DRIFT-TRACE-HOME (truy nguyên thay đổi băm của chỉ mục production máy nhà — chỉ đọc tuyệt đối)

- Mã vé: `INDEX-HASH-DRIFT-TRACE-HOME`
- Role gợi ý: PLAN (truy nguyên bằng chứng, không sửa)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/index-hash-drift-trace-home.md`
- Căn cứ: vé `UI-ANSWER-QUALITY-HOME` bị verdict CHƯA ĐẠT. Trong phiên đo `CONV-QUALITY-6709BE`, SHA-256 của chỉ mục production `library.sqlite` đã đổi từ `45EB0E07…B7C0` (chuẩn đã đóng dấu, khớp tuyệt đối qua mọi vé trước) sang `B0B873D0…3EE6`, dung lượng không đổi (2.942.201.856 byte). Giải trình của vé trước: app gọi `prepare_sources_for_workspace_chat` với `read_only=False` khi bật thêm nguồn, SQLite cập nhật file change counter ở header. NHƯNG cùng báo cáo đó ghi tổng số mảnh là **149.827** trong khi chuẩn đã khép nhiều lớp (SRC-PROBE, FP-TOTAL-RECONCILE) là **149.800** — lệch +27 chưa có lời giải. Truy nguyên phải khép cả hai điểm.

## Việc phải làm

1. **Kiểm kê trạng thái hiện tại của chỉ mục** (mở `mode=ro&immutable=1`): `PRAGMA integrity_check` + `PRAGMA quick_check`; đếm: tổng tài liệu (chuẩn 889), tổng mảnh (chuẩn 149.800), mảnh truy hồi được (chuẩn 121.331). Đếm thêm theo từng bảng/loại mảnh để định vị con số 149.827 của vé trước đến từ cách đếm nào hoặc bảng nào.
2. **Xác định thay đổi vật lý:** đọc header SQLite của tệp hiện tại (file change counter, schema cookie, version-valid-for number, application_id, user_version) và mọi bằng chứng sẵn có về header ở trạng thái đã đóng dấu (log/báo cáo các vé trước nếu có ghi). Trả lời dứt khoát: thay đổi chỉ nằm ở header (dữ liệu không đổi byte nào) hay có trang dữ liệu nào đã đổi? Nếu có công cụ so sánh theo trang với một bản sao đã kiểm chứng trên cùng máy (nếu còn tồn tại) thì dùng; không có thì nêu rõ giới hạn chứng minh.
3. **Truy đường code mở ghi:** liệt kê mọi điểm trong đường hỏi đáp/giao diện thường mở kết nối ĐỌC-GHI vào chỉ mục production (điểm `prepare_sources_for_workspace_chat` với `read_only=False` và mọi điểm tương tự), kèm file:dòng và điều kiện kích hoạt. Đây là gốc của bệnh "chuẩn bị nguồn" đã ghi nhận ở mô hình tài liệu.
4. **Kết luận thuộc đúng 1 trong 3 nhánh, kèm đề xuất:**
   - (a) Chỉ header đổi, dữ liệu nguyên vẹn → đề xuất cách xử lý để các phiên sau không phá bất biến nữa + có cần khôi phục băm gốc không và bằng cách nào an toàn (chỉ đề xuất — KHÔNG tự khôi phục).
   - (b) Dữ liệu có thay đổi thật → mô tả thay đổi (bảng nào, bao nhiêu dòng, nội dung loại gì), đánh giá ảnh hưởng tới hỏi đáp, đề xuất khôi phục từ bản đã kiểm chứng.
   - (c) Con số 149.827 là do cách đếm khác → chứng minh bằng cách chạy cả hai cách đếm trên cùng chỉ mục và chỉ ra khác biệt nằm ở đâu.
5. **Đề xuất vé sửa điểm nối:** để đường giao diện tôn trọng chỉ mục chỉ đọc khi hỏi đáp (điểm nối cụ thể file:hàm), chờ điều phối duyệt mới sửa.

## Rào cứng

- CHỈ ĐỌC TUYỆT ĐỐI với chỉ mục production: mọi kết nối đều `mode=ro&immutable=1`. Cấm ghi, cấm vacuum, cấm khôi phục, cấm mở app theo đường có thể ghi vào chỉ mục trong suốt vé này.
- Cấm chạy thêm bất kỳ phiên đo/nghiệm thu nào trên app cho tới khi điều phối có kết luận từ báo cáo này (lệnh đóng băng đã ghi ở mailbox).
- Mọi con số trong báo cáo phải kèm lệnh/cách đếm tái lập được. Không merge `main`.
