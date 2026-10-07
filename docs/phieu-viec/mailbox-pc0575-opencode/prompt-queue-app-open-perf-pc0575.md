# VÉ: APP-OPEN-PERF-PC0575 (mở sổ trò chuyện chậm mấy phút + khối sổ xấu)

- Mã vé: `APP-OPEN-PERF-PC0575`
- Role gợi ý: DEFAULT (đo + code UI/hiệu năng)
- Máy: công ty KDTVN-PC0575 (máy yếu nhất — đích triển khai LAN)
- Báo cáo: `docs/phieu-viec/ket-qua/app-open-perf-pc0575.md`
- Điều kiện bốc vé: xếp hàng sau `SRC-PROBE-PC0575` trong mailbox này.
- File chính: `src/aios_habit/workspace_chat_app.py` (KHÔNG đụng `src/rag_v2*` — WIP của agy; không đổi ngữ nghĩa retrieval/synthesis).

## Bối cảnh (user báo trực tiếp 07/10 kèm ảnh chụp app thật)

1. **Bấm vào sổ trò chuyện phải chờ mấy phút mới lên.** Ảnh chụp cho thấy khi vào sổ, app hiện "AIOS đang chuẩn bị N tài liệu ở chế độ nền" và thanh "Đã chuẩn bị xong 33/35 tài liệu (94%) — Việc chuẩn bị đang tạm dừng". Trong code đã thấy manh mối: khi nạp trang, app lên lịch chuẩn bị nguồn (`_schedule_sources_for_preparation`, ghi chú quanh dòng 5135 "Only prepare enabled sources on page load...") — chuẩn bị = cắt mảnh + nhúng bằng model trên CPU của laptop không GPU, rất chậm. Cần ĐO để kết luận phần nào của đường mở sổ đang chặn đồng bộ, không đoán.
2. **Khối sổ trò chuyện / danh sách cuộc trò chuyện nhìn xấu, mất thẩm mỹ**: bố cục thưa, chữ nhỏ mờ, các khối rời rạc thiếu phân cấp thị giác (ảnh user gửi 18:38 07/10, xem trong mailbox/hội thoại điều phối).

## Phần 1 — Đo và sửa tốc độ mở sổ (bắt buộc trước)

1. Đo đường mở sổ trên máy thật: bấm mở sổ "Điều tra lỗi LSU" (494 tài liệu) và 1 sổ nhỏ; ghi thời gian từ lúc bấm tới khi (a) thấy danh sách cuộc trò chuyện, (b) gõ được câu hỏi. Phân rã thời gian theo chặng: nạp trang, lên lịch/chạy chuẩn bị nguồn, nạp model nhúng, nạp chỉ mục/vector, tải lịch sử trò chuyện. Mọi khẳng định phải có số đo, không suy luận.
2. Sửa để đạt: **mở sổ thấy nội dung và gõ được trong ≤3 giây** trên PC0575 với sổ LSU. Nguyên tắc: mọi chuẩn bị tài liệu là việc nền THẬT — không chặn đường mở, không chạy đồng bộ trong lượt nạp trang; tiến độ nền hiển thị gọn, không chiếm khối lớn; lịch sử trò chuyện tải lười theo nhu cầu.
3. Giữ nguyên hành vi hỏi-đáp và các rào đã có (vd luật FR-006/FR-011: 1 câu hỏi tương tác chỉ tự chuẩn bị tối đa 1 nguồn). Không đánh đổi chất lượng trả lời lấy tốc độ mở.

## Phần 2 — Làm đẹp khối sổ + danh sách trò chuyện

1. Chỉnh các khối trong ảnh: thẻ sổ (tên, trạng thái, số tài liệu), danh sách cuộc trò chuyện, khối chuyên gia — phân cấp chữ rõ, khoảng cách đều, trạng thái dùng màu/chấm nhất quán, bỏ các dòng chữ thừa lặp lại. Giữ đúng hướng chat-first tối giản: không thêm nút/toolbar mới.
2. Báo cáo kèm **ảnh trước/sau chụp trên app thật** để user nghiệm thu bằng mắt.

## Kiểm chứng & báo cáo

- Số đo trước/sau cho cả 2 sổ (mở lạnh + mở lại), chụp ảnh trước/sau.
- Cổng kiểm chứng repo: compileall + pytest liên quan + `cli audit` + import app; tương thích Python 3.11.
- Metric vòng cải thiện: thời gian mở sổ (giây) ghi trong báo cáo là metric chuẩn — các vé UI sau đối chiếu trên cùng thước.
- **NGHIỆM THU DÙNG THẬT LÀ CHÍNH (user chốt 18:42 07/10):** mọi số đo và ảnh trong vé này phải lấy từ việc **dùng app thật trên máy thật** (tự động hoá thao tác mở sổ/hỏi đáp như người dùng cuối). Test file chỉ phụ trợ giữ hồi quy, không thay thế.
- **PHỤ THUỘC APP-SOURCE-MODEL (bổ sung 19:05 07/10):** phần việc liên quan tới khâu "chuẩn bị tài liệu" trong vé này phải chờ kết luận chặng 1 của vé `APP-SOURCE-MODEL-PC0575` (điều phối duyệt hướng mô hình hợp nhất xong mới sửa phần chuẩn bị — tránh vá trên mô hình sắp bỏ). Phần đo đường mở sổ + phân rã thời gian vẫn làm bình thường.
