# Hướng dẫn dùng thử nhanh — phân tích log JIG trên AIOS Workspace Chat

Nguyên tắc giao diện: **1 ô nhập + 1 vùng trả lời**. Mọi thao tác gõ vào một ô nhập duy nhất ở cuối khung chat; kết quả (chữ, bảng, biểu đồ) hiện ở vùng trả lời. Không phải mở bảng cài đặt hay bấm nút rải rác — chỉ riêng việc **chọn tệp từ máy của bạn** nằm ở khu "Cổng dữ liệu LSU" (thanh bên).

## 0. Mở app

- Mở địa chỉ app do quản trị đưa (ví dụ `http://<địa-chỉ-máy>:8501`), vào một sổ bất kỳ để dùng khung chat.
- Ô nhập nằm dưới cùng — gõ tiếng Việt bình thường, không cần cú pháp lập trình.

## 1. Nạp dữ liệu log JIG

### Cách A — nạp tệp từ máy bạn (dùng được ngay cả khi truy cập qua LAN; đây là cách nạp để vẽ biểu đồ)

1. Mở mục **"🔍 Cổng dữ liệu LSU (chế độ chạy ngầm)"** ở thanh bên.
2. Vào tab **"📋 Cổng kiểm tra dữ liệu"**, chọn kiểu **"Log JIG Iris (một tệp, xuất thẳng từ máy)"**.
3. Kéo–thả tệp log vào ô **"Tệp log JIG Iris (nhận mọi loại log đo)"** — nhận cả log rộng (UnitTest) lẫn log đo sâu (Depth/Profile). Nếu có tệp giới hạn kèm theo (`2026_08_Spec.csv`, `2026_08_CamPos.csv`) thì đính kèm luôn ở ô bên dưới để nạp ngưỡng thật.
4. Bấm **"🚀 Đọc log Iris và kiểm tra"** — hệ thống tự nhận định dạng, bỏ các ô canh lỗi và lưu giá trị vào kho log.
5. Quay lại khung chat để hỏi biểu đồ / đặt ngưỡng (mục 2–4 dưới đây).

### Cách B — nhập cả tệp bằng lệnh chat (tệp đã nằm trên máy chạy app)

Gõ vào ô nhập: `nhập tệp log "D:\DuLieu\IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv"`

- Đặt trong dấu ngoặc kép nếu đường dẫn có dấu cách.
- Trả lời thật khi thử với tệp log thật (24,4 MB): *"Đã nhập 50.000 giá trị đo từ tệp IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv (ma trận rộng Iris) vào kho log."*
- Nhập lại cùng tệp không đổi → bỏ qua: *"Tệp … đã nhập trước đó và nội dung không đổi, nên hệ thống bỏ qua để tránh ghi trùng."*
- Tệp lớn hơn 50.000 giá trị: app báo rõ số còn lại chưa lưu — chia nhỏ tệp nếu cần lưu hết.

### Cách C — dán thẳng dòng log vào ô nhập

Dán một dòng log JIG theo dạng: `thời gian, mã Unit, mã JIG, chỉ số, giá trị, đơn vị, trạng thái`

Ví dụ dòng thật đã dùng khi thử: `2026-10-01T10:00:00,61C1068E6222,IrisLSU (log dán),SKEW:BLACK,-359,um,OK`

→ Nhận ngay **thẻ kết luận** cho dòng đó (Bình thường / Cận biên / Vi phạm).

### Xem lại kho đã nạp

- Gõ `xem kho log` → bảng tóm tắt: số dòng, mã JIG, số Unit, danh sách chỉ số.

> **Lưu ý quan trọng:** lệnh vẽ biểu đồ lấy dữ liệu từ lần nạp ở **Cách A** (dữ liệu đang xem trong phiên). Nếu chưa nạp gì, hệ thống trả đúng câu: *"Chưa có dữ liệu để vẽ biểu đồ. Vui lòng mở mục Kiểm tra dữ liệu LSU, tải tệp và chờ báo dữ liệu hợp lệ trước."*

## 2. Xem biểu đồ

| Muốn gì | Gõ vào ô nhập |
|---|---|
| Xu hướng theo thời gian | `chọn biểu đồ xu hướng` |
| Phân bố giá trị | `chọn biểu đồ phân bố` |
| So sánh nhiều màu (nhiều chỉ số) | `chọn biểu đồ so sánh màu` |
| Chọn đích danh một chỉ số | `chọn biểu đồ phân bố cho SKEW:BLACK` |

Ảnh hiện ngay trong vùng trả lời kèm câu xác nhận, ví dụ: *"Đã chọn Phân bố giá trị cho … — SKEW:BLACK (áp dụng ngay). Ảnh đã lưu vào phiên để xem lại ở Thẻ 1 và dùng cho email cảnh báo."*

## 3. Đặt ngưỡng cảnh báo

| Muốn gì | Gõ |
|---|---|
| Đặt giới hạn trên | `đặt ngưỡng trên -364 cho SKEW:BLACK` |
| Đặt giới hạn dưới | `đặt ngưỡng dưới 1.2 cho BOW:BLACK:0` |
| Xem lại ngưỡng | `xem ngưỡng` |
| Xóa ngưỡng | `xóa ngưỡng SKEW:BLACK` |

Khi dán một dòng log vượt ngưỡng, kết luận ghi rõ nguồn ngưỡng — ví dụ thật: *"Giá trị -359 vượt giới hạn trên -364 của SKEW:BLACK (nguồn: nguoi_dung)."* — và hệ thống tự vẽ biểu đồ đã cấu hình để đính kèm mail cảnh báo (mục 4).

## 4. Cấu hình mail cảnh báo

| Muốn gì | Gõ |
|---|---|
| Thêm người nhận | `thêm email to.truong@congty.local` |
| Bớt người nhận | `xóa email to.truong@congty.local` |
| Đổi mức kích hoạt | `đổi ngưỡng 90%` |
| Giãn cách chống spam | `đổi giãn cách 60 phút` |
| Chọn biểu đồ gửi kèm | `chọn biểu đồ gửi mail phân bố` |
| Bỏ biểu đồ gửi kèm | `bỏ biểu đồ gửi mail xu hướng` |

- Sau mỗi lệnh, hệ thống in lại **"Bảng cấu hình cảnh báo"** ngay trong chat để xem lại.
- **Không tự gửi mail**: khi cảnh báo kích hoạt, hệ thống chỉ tạo **thẻ đề xuất** kèm mã duyệt (ví dụ `DUYET-593BE3D4`); chỉ gửi sau khi người dùng **duyệt tay**.

## 5. Cảnh báo xu hướng (EWMA)

Khi chỉ số chưa có ngưỡng do bạn đặt, hệ thống vẫn đối chiếu xu hướng trôi dốc. Ví dụ thật: *"Xu hướng EWMA lệch 393.111 vượt ngưỡng 92.941, cần kiểm tra."* — kết luận "Vi phạm" nêu rõ là theo EWMA, không phải theo giới hạn sản xuất.

## 6. Ví dụ một lượt đầy đủ (đã chạy thật trên dữ liệu thật)

1. Nạp tệp log theo **Cách A** (hoặc Cách B nếu tệp nằm trên máy chạy app).
2. Gõ `chọn biểu đồ phân bố` → nhận ảnh.
3. Gõ `đặt ngưỡng trên -364 cho SKEW:BLACK` → nhận bảng ngưỡng.
4. Gõ `thêm email ca-test@nhay.local` → `chọn biểu đồ gửi mail phân bố` → `bỏ biểu đồ gửi mail xu hướng`.
5. Dán dòng `2026-10-01T10:00:00,61C1068E6222,IrisLSU (log dán),SKEW:BLACK,-359,um,OK`
   → nhận kết luận **"Vi phạm"** + biểu đồ phân bố + thẻ đề xuất mail; duyệt gửi nếu cần.

## 7. Ghi nhận phản hồi (phần quan trọng nhất của đợt dùng thử)

Mọi vướng mắc, câu trả lời khó hiểu, số liệu trông sai, mong muốn thay đổi:

- Ghi **nguyên văn câu đã gõ + câu trả lời nhận được** vào `02-MAU-BIEN-BAN-DUNG-THU.md`.
- Gom các đề xuất cải tiến vào `03-MAU-BACKLOG-CAI-TIEN.md` (có thứ tự ưu tiên).
