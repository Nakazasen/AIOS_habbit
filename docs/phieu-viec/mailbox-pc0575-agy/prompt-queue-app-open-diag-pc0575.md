# VÉ: APP-OPEN-DIAG-PC0575 (phân rã và xử lý thời gian mở sổ 2–3 phút — phản ánh trực tiếp của user)

- Mã vé: `APP-OPEN-DIAG-PC0575`
- Role gợi ý: DEFAULT
- Máy: công ty KDTVN-PC0575 (agy — thợ chính, CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/app-open-diag-pc0575.md`
- Căn cứ: user tự đo tại máy công ty tối 08/10/2026 kèm ảnh chụp: app khởi động lại lúc 19:06 (log Uvicorn trong ảnh), sau đó **bấm vào sổ MOM mất khoảng 2–3 phút mới vào được**; trước đó bấm vào sổ LSU cũng chậm như hôm qua. Đây là số đo dùng thật của người dùng cuối trên phiên app MỚI (đã loại trừ lý do "phiên cũ chưa nạp code") — mức 120–180 giây cho một thao tác mở sổ là không chấp nhận được (mục tiêu trải nghiệm đã chốt: mở sổ/gõ được câu hỏi trong vài giây). Vé chặng 2 của `APP-SOURCE-MODEL-PC0575` vừa tắt chuẩn bị tự động nhưng thời gian mở không cải thiện ở mức user cảm nhận được → thủ phạm nằm ở khâu khác, phải phân rã bằng số đo chứ không đoán.

## Việc phải làm

1. **Đo phân rã (bắt buộc trước khi sửa):** gắn mốc thời gian (log có timestamp từng bước) cho toàn bộ đường mở sổ, đo riêng: (a) bấm vào sổ MOM — lần mở đầu tiên sau khi khởi động lại app (lạnh); (b) bấm vào sổ MOM lần thứ hai (ấm); (c) bấm vào sổ LSU (NB-E35A7BEE) lần đầu và lần hai. Từng lần phải tách được thời gian của các khâu: tải/khởi tạo trang, liệt kê cuộc trò chuyện, đọc metadata sổ, chuẩn bị/phạm vi nguồn, nạp mô hình/worker nền (nếu bị kích hoạt khi mở sổ), truy vấn cơ sở dữ liệu hội thoại, các khâu khác phát hiện được. Nộp bảng phân rã: khâu nào ăn bao nhiêu giây, khâu nào chiếm phần lớn trong 120–180 giây.
2. **Sửa đúng khâu chiếm phần lớn** theo bằng chứng ở bước 1 (ví dụ minh hoạ hướng, không áp đặt: trì hoãn nạp việc nặng tới lúc hỏi câu đầu thay vì lúc mở sổ; bộ nhớ đệm có kiểm chứng cho metadata/đếm theo khối; bỏ quét lặp toàn kho mỗi lần mở). Mỗi thay đổi phải có test hồi quy và ghi rõ cơ chế hoàn lui.
3. **Đo lại đúng thao tác của user** sau khi sửa: khởi động lại app → bấm sổ MOM → bấm sổ LSU, ghi số giây từng lần (lạnh/ấm) kèm ảnh chụp có nội dung sổ trong khung. Cổng đạt của vé: lần mở ấm ≤ 10 giây cho cả hai sổ; lần mở lạnh có bảng phân rã khép kín (tổng các khâu khớp thời gian toàn trình ±20%) và nếu vẫn > 30 giây thì nêu rõ phần còn lại là gì + đề xuất vé tiếp theo — không ghi "đã nhanh" khi số đo chưa đạt.

## Rào cứng

- Không ghi chỉ mục (MD5 trước/sau mọi phiên đo phải khớp). Không thay đổi hành vi hỏi đáp/truy hồi; phạm vi chỉ ở đường mở sổ/nạp trang.
- Không merge `main`. Tương thích Python 3.11. Mốc tiến độ tối thiểu 15 phút/lần + checkpoint/resume.
- Mọi con số trong báo cáo phải tái lập được từ log phân rã đính kèm (nộp file log thô vào `docs/phieu-viec/ket-qua/`).
