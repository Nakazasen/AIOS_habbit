# Ticket chuan-bi-tai-lieu-lsu — Chuẩn bị tài liệu cho sổ "Điều tra lỗi LSU" (171 nguồn)

## Bối cảnh
- App báo "Đã chuẩn bị xong 0/171 tài liệu (0%)" trong sổ "Điều tra lỗi LSU": 171 nguồn đang bật chưa có vector.
- Sổ này dùng collection `tri_thuc` (mặc định theo code) → vector của 171 nguồn sẽ được app ghi THÊM vào `library.sqlite` hiện có. Đây là hành vi chuẩn của nút "Thử chuẩn bị lại": chỉ thêm mới, không sửa/xóa vector cũ (app kiểm fingerprint, vector nào khớp thì bỏ qua). Không phải ghi đè index.
- 171 tài liệu nhỏ (vector thêm vào chỉ cỡ chục/hàng trăm MB, không tới GB). Index 2.4GB / 107.331 vector cũ không bị embed lại.

## Việc cần làm
0. Verify backup P5 `C:\AIOS_p5\library.sqlite.bak-20260930`: SHA-256 phải là `062EC090644FB4EC09D2FB6388F3175E988E48D63061B04E6C27BBED334EF8CA` và `PRAGMA integrity_check` = ok. Không khớp → dừng, đặt `cho-muse`.
1. Mở app `http://127.0.0.1:8501`, vào sổ "Điều tra lỗi LSU".
2. Bấm nút "Thử chuẩn bị lại". Để app chạy — không tắt app, không tắt máy. Máy này CPU-only nên có thể mất hàng chục phút, cứ để chạy hết.
3. Theo dõi tiến độ "Đã chuẩn bị xong x/171" đến khi đạt 171/171 và thông báo "chưa sẵn sàng" biến mất.
4. Verify sau chạy: `PRAGMA integrity_check` = ok trên `library.sqlite`; số vector chỉ được tăng (tuyệt đối không giảm).
5. Chụp màn hình kết quả cuối. Báo cáo: `docs/phieu-viec/ket-qua/chuan-bi-tai-lieu-lsu.md` — số tài liệu hoàn tất, thời gian chạy, kết quả verify, ảnh chụp.

## Cấm
- Chỉ làm với 171 nguồn đang bật của sổ này; không bật thêm nguồn mới (đặc biệt chưa mở sổ "MOM / Opcenter" khi chưa được duyệt).
- Không xóa/sửa vector cũ, không re-embed toàn bộ index.
- Không merge `main`. Không đụng ổ D máy nhà.
