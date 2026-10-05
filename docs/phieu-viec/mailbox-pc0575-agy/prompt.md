# Mailbox thợ agy — máy công ty KDTVN-PC0575

**Thợ:** agy (Antigravity CLI)
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
**Thư mục làm việc DUY NHẤT:** `D:\Sandbox\AIOS_habbit`
**Trạng thái:** chưa có ticket — mailbox mới tạo, chờ phân công.

## Luật thợ (bắt buộc)

1. Chỉ làm trong `D:\Sandbox\AIOS_habbit`. Không đụng ổ D máy nhà, không đụng máy khác.
2. Quy trình mailbox: nhận vé khi `trang-thai.md` → `moi` → đặt `dang-lam` khi bắt đầu,
   ghi `ghi_chu` mốc tiến độ, xong thì viết báo cáo vào `docs/phieu-viec/ket-qua/` rồi
   đặt `trang-thai.md` → `xong-cho-duyet`.
3. Commit sớm, push qua Git Data API ngay khi có commit hoàn chỉnh. Không dồn cuối.
4. Không merge `main`. Không force-push. Không xóa dữ liệu/backup khi chưa có lệnh user.
5. Code mới phải tương thích Python 3.11 (không dùng syntax 3.12+).
6. Watcher tự mở thợ khi có vé mới; nếu 4 lần mở mà mailbox không tiến triển, watcher
   tự dựng cờ `cho-muse` — khi đó DỪNG, chờ Muse xử lý, không tự ý làm tiếp.

## Khi chưa có ticket

Giữ mailbox ở trạng thái `trong`. Không tự nhận việc ngoài vé. Chờ Muse phát vé mới
(vé sẽ được copy vào file này, `trang-thai.md` → `moi`).
