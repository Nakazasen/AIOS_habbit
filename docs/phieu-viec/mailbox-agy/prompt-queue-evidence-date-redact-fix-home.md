# Vé: EVIDENCE-DATE-REDACT-FIX-HOME — sửa lỗi bộ che dữ kiện ăn nhầm chuỗi ngày trong văn bản bằng chứng

**Phát hành:** điều phối Muse, 2026-10-11 ~21:0x +07. **Hàng chờ:** bốc sau `RAG-RETRIEVAL-NUMPY-COMPLETE-HOME` và `DISK-GROWTH-DIAG-HOME`.
**Báo cáo:** `docs/phieu-viec/ket-qua/evidence-date-redact-fix-home.md`

## Triệu chứng đã kiểm chứng (verdict DESKTOP-LSU-TARGET-A5-HOME, 2026-10-11)

Ở đường bằng chứng truy hồi (RAG evidence) đưa vào tổng hợp, các chuỗi ngày dạng `2026/08/20` trong văn bản bằng chứng bị thay bằng `[REDACTED_LOCAL_PATH]`. Hệ quả tại phiên A5: câu biến thể về serial `61C999999902` trong tệp `2026_08_UnitTest.csv` trả lời đúng toàn bộ phán định nhưng **không nêu được ngày nào** vì cả hai mốc ngày trong bằng chứng đều bị che; đáp án phải tự ghi "ngày cụ thể không đọc được". Câu Q0824 đi đường làn cấu trúc thì ngày còn nguyên — lỗi nằm ở khâu đóng gói/che bằng chứng của đường truy hồi, không nằm ở làn cấu trúc.

## Việc phải làm

1. Tìm logic che dữ kiện sinh ra `[REDACTED_LOCAL_PATH]` (rà toàn bộ mã theo chuỗi này) và xác định vì sao chuỗi ngày khớp mẫu "đường dẫn cục bộ". Ghi rõ gốc rễ vào báo cáo (tệp + dòng + mẫu biểu thức).
2. Sửa để: chuỗi ngày (dạng `yyyy/mm/dd`, `yyyy-mm-dd`, `dd/mm/yyyy`) trong văn bản bằng chứng **không bị che**; đường dẫn cục bộ thật (ổ đĩa Windows, UNC, thư mục người dùng) **vẫn bị che như cũ**. Không nới lỏng các lớp che khác (key, token, dữ kiện cá nhân).
3. Thêm test hồi quy hai chiều: (a) văn bản bằng chứng chứa ngày giữ nguyên ngày sau khi qua khâu che; (b) văn bản chứa đường dẫn cục bộ thật vẫn bị che. Chạy đủ 4 cổng chất lượng của repo (compileall + pytest + cli audit + import app) trên Python tương thích 3.11.
4. Nghiệm thu trên giao diện thật (chuẩn sản phẩm): hỏi lại qua giao diện, trên khối `lsu`, câu "Trong tệp 2026_08_UnitTest.csv, serial 61C999999902 có kết quả kiểm tra như thế nào qua các ngày?" — đáp án phải đọc được mốc ngày cụ thể. Chụp ảnh hoàn tất trọn thân đáp án, khai commit HEAD + cấu hình hiệu lực (CPU-only) trong báo cáo. Áp cổng bằng chứng bản siết 11/10 (ảnh không trùng byte, trạng thái hoàn tất).
