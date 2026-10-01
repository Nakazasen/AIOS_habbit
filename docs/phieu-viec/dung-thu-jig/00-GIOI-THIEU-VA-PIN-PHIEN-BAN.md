# Gói dùng thử JIG — giới thiệu và phiên bản đã ghim

Bộ tài liệu này phục vụ **Bước 3 kế hoạch công ty**: "Triển khai dùng thử, thu thập thông tin cải tiến" (hạn 15/11/2026 — xem `docs/dich-den-du-an.md` mục 2). Vé J3 là vé **chuẩn bị + ghi nhận**: OMP/Muse chuẩn bị gói và công cụ ghi nhận; người dùng công ty dùng thử trên việc thật rồi trả phản hồi.

## 1. Gói gồm những gì

| Tệp | Dùng để |
|---|---|
| `00-GIOI-THIEU-VA-PIN-PHIEN-BAN.md` | Tài liệu này — bản dùng thử là gì, ghim phiên bản nào, ai mở, điều kiện chạy |
| `01-HUONG-DAN-SU-DUNG-NGAN.md` | Hướng dẫn thao tác cho người dùng công ty (1 ô nhập + 1 vùng trả lời) |
| `02-MAU-BIEN-BAN-DUNG-THU.md` | Mẫu biên bản: ai dùng, dùng vào việc gì, phản hồi gì |
| `03-MAU-BACKLOG-CAI-TIEN.md` | Mẫu backlog cải tiến có thứ tự ưu tiên (chờ user chốt) |

## 2. Bản dùng thử là gì — phiên bản đã ghim

- Công cụ: các chức năng JIG trong app **AIOS Workspace Chat** — nhập tệp log JIG (cả tệp CSV hoặc dán dòng log), chọn biểu đồ, đặt ngưỡng cảnh báo, cảnh báo xu hướng, cấu hình mail cảnh báo kèm biểu đồ.
- Mã chức năng JIG **đã được vé J2 xác nhận trên dữ liệu thật**: commit `5bb837e` trên nhánh `phieu-viec/rag-fix1` — biên bản 17/17 mục PASS, 39/39 probe API, 41/41 test vé, 4/4 cổng nền; báo cáo `docs/phieu-viec/ket-qua/j2.md`; verdict ĐẠT 2026-10-02 ~00:55 +07.
- Kiểm tra tính đúng của ghim: từ `5bb837e` tới khi đóng gói, phần `src/` + `tests/` chỉ đổi đúng 1 commit `4a796ac` — sửa token cache trong `src/aios_habit/rag_v2/index.py` (Phase A của vé `OPT-RAGV2-LEXICAL`, KHÔNG thuộc JIG, chờ verify riêng trên PC0575 theo hàng chờ của máy đó). Mọi tệp chức năng JIG (`src/aios_habit/production_prediction/`, phần nối chat trong `workspace_chat_app.py`) **không đổi** so với `5bb837e`.
- Vì vậy khi mở bản dùng thử: dùng `5bb837e` nếu muốn đúng cây đã verify J2 (`git checkout 5bb837e`); hoặc `git pull` tới `5bb837e` trở lên nếu chấp nhận kèm commit RAG v2 ở đỉnh nhánh.
- Tệp CSV mẫu dùng khi verify (ví dụ trong hướng dẫn): `IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv` — 24.375.633 B, SHA-256 `6ebf2930…441c` (log thật dòng máy, chỉ dùng làm ví dụ số liệu).

## 3. Ai mở bản dùng thử (phần kỹ thuật ngắn)

1. Trên máy chạy app phục vụ người dùng (máy công ty): `git pull origin phieu-viec/rag-fix1` (tối thiểu `5bb837e`).
2. Khởi động lại app bằng `RUN_AIOS_WORKSPACE_CHAT.bat`; kiểm tra `/_stcore/health` trả `ok`.
3. Nếu máy khác trong LAN chưa mở được app: xử lý firewall cổng 8501 theo ghi chú tại `docs/phieu-viec/ket-qua/p5b-mang-moi.md` mục 5 (cần quyền quản trị).
4. Người dùng mở địa chỉ app do quản trị đưa (ví dụ `http://<địa-chỉ-máy>:8501`) và làm theo `01-HUONG-DAN-SU-DUNG-NGAN.md`.

## 4. An toàn dữ liệu và giới hạn đã biết

- **Không tự gửi mail**: hệ thống soạn thẻ đề xuất kèm mã duyệt; chỉ gửi sau khi người dùng duyệt tay.
- Chỉ số chưa có giới hạn thật hiển thị nhãn `[MÔ PHỎNG]` — không tự nhận là giới hạn sản xuất.
- Mỗi lần nhập tối đa 50.000 giá trị; tệp lớn hơn cần chia nhỏ (app báo rõ số còn lại chưa lưu).
- Nhập lại cùng một tệp không đổi → hệ thống bỏ qua (chống trùng cấp tệp).
- Dữ liệu log người dùng nạp được lưu trong kho log cục bộ của app; không ghi vào chỉ mục RAG, không đụng `main`.
- Khi gửi phản hồi kèm ảnh chụp màn hình: kiểm tra ảnh không chứa nội dung nội bộ ngoài phạm vi cần minh họa.

## 5. Sau khi dùng thử

- Điền `02-MAU-BIEN-BAN-DUNG-THU.md` (mỗi người × mỗi lượt một khối) và `03-MAU-BACKLOG-CAI-TIEN.md`.
- Gửi lại cho đầu mối AIOS để tổng hợp. Biên bản + backlog chỉ được coi là **chốt** khi có xác nhận của người dùng/trưởng nhóm — đúng tiêu chí ĐẠT của vé J3.
