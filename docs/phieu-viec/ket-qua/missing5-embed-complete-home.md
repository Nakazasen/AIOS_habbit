# Báo cáo đóng vé: MISSING5-EMBED-COMPLETE-HOME (ĐÃ HUỶ)

- Mã vé: `MISSING5-EMBED-COMPLETE-HOME`
- Trạng thái kết thúc: `HUY-BO` (theo quyết định điều phối Muse và chỉ đạo của User 2026-10-11 ~11:00 +07)
- Thời điểm đóng: 2026-10-11 11:12:00 +07
- Máy thực thi: `h410asrock` (Agent AGY)

---

## 1. Lý do huỷ vé

Theo quyết định của Điều phối Muse và chỉ đạo của User:
Hai tệp đích (`2026_08_Error_BowOverAdjust.csv` và `2026_08_Spec.csv`) là dữ liệu log/bảng dạng cấu trúc. Các mục đích sản xuất của chúng (cảnh báo xu hướng SMA(20), thẻ cảnh báo thời gian thực, phát hiện lỗi phòng ngừa) đều vận hành trên đường số liệu có cấu trúc, không dùng vector. Hỏi đáp trên dữ liệu này cần làn truy vấn có cấu trúc (structured lane) kết hợp kênh từ khóa FTS, việc nhúng vector dày cho hàng chục nghìn dòng log không phục vụ mục đích sản xuất. Do đó, tiến trình nhúng được dừng an toàn tại biên điểm kiểm gần nhất và huỷ bỏ phần còn lại để chuyển ưu tiên sang vé sửa lệch khối `Q0668-BLOCK-FIX-HOME` và vé làn cấu trúc `CSV-STRUCTURED-LANE-HOME`.

---

## 2. Số liệu kiểm kê tại thời điểm dừng an toàn

- **Vị trí cơ sở dữ liệu production**: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Kích thước file**: 3.400.540.160 bytes (~3,40 GB)
- **SHA-256 sau khi dừng**: `957f35d2206171b7ee8887d766b12aab57222828748cb87a84b1fe7e8c757332`
- **Kiểm tra toàn vẹn (`PRAGMA integrity_check`)**: `ok`
- **Tổng số mảnh trong DB**: 181.511 mảnh
- **Tổng số mảnh có thể truy xuất (retrievable=1)**: 149.350 mảnh
- **Số mảnh đã nhúng hoàn tất trước khi dừng**: 11.008 / 26.907 mảnh (đạt 40,91%)
  - `2026_08_Spec.csv` (document `wsc-d4df39c14101e40ebad88a91`): **4.853 / 4.853 mảnh (100% hoàn thành)**
  - `2026_08_Error_BowOverAdjust.csv` (document `wsc-8eb2a5d21b75fa88307223b1`): **6.155 / 22.054 mảnh (27,91%)**
- **Tổng số vector dày (dense) hiện tại**: **133.791** vector (tăng từ 122.783, +11.008 vector mới)
- **Tổng số vector thưa (sparse) hiện tại**: **133.791** vector

---

## 3. Bảo toàn dữ liệu & trạng thái

- Tiến trình nhúng đã dừng sạch sẽ tại biên điểm kiểm batch 64 mảnh, transaction đã commit trọn vẹn.
- Toàn bộ 11.008 vector dày và thưa đã tạo được giữ nguyên vẹn trong DB production làm dữ kiện hợp lệ, không gỡ bỏ.
- Cơ sở dữ liệu đạt trạng thái toàn vẹn 100%, sẵn sàng cho các vé tiếp theo.
