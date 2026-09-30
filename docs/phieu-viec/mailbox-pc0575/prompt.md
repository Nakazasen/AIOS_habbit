# Ticket chuan-bi-tai-lieu-lsu — Chuẩn bị tài liệu cho sổ "Điều tra lỗi LSU" (171 nguồn)

## Bối cảnh
- App trên PC0575 báo "Đã chuẩn bị xong 0/171 tài liệu (0%)" trong sổ "Điều tra lỗi LSU": 171 nguồn đang bật chưa có vector nên tìm kiếm đầy đủ chưa sẵn sàng. Đây là việc tồn (b) từ vé P5.
- P5/P5b đã ĐẠT và đóng; vé này xử lý nốt phần tài liệu.

## Việc cần làm
1. Mở app `http://127.0.0.1:8501`, vào sổ "Điều tra lỗi LSU".
2. Bấm nút "Thử chuẩn bị lại". Để app chạy — không tắt app, không tắt máy. Máy này chỉ có CPU nên bước này có thể mất hàng chục phút, cứ để nó chạy hết.
3. Theo dõi tiến độ "Đã chuẩn bị xong x/171" cho đến khi đạt 171/171 và thông báo "chưa sẵn sàng" biến mất.
4. Chụp màn hình kết quả cuối. Báo cáo: `docs/phieu-viec/ket-qua/chuan-bi-tai-lieu-lsu.md` — số tài liệu hoàn tất, thời gian chạy, ảnh chụp màn hình.

## Cấm
- Chỉ làm với 171 nguồn đang bật của sổ này; không bật thêm nguồn mới (đặc biệt chưa mở sổ "MOM / Opcenter" khi chưa được duyệt).
- Không embed lại / không ghi đè index production (`C:\AIOS_p1_4\tri_thuc\library.sqlite`).
- Không merge `main`. Không đụng ổ D máy nhà.
