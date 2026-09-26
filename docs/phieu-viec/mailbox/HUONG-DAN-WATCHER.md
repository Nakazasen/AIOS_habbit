# Watcher Windows — tự động nhắc OMP khi có ticket mailbox mới

## Nó làm gì

Script `Watch-Mailbox.ps1` chạy nền trên máy Windows, mỗi ~90 giây đọc
`docs/phieu-viec/mailbox/trang-thai.md` trên GitHub:

- Thấy ticket mới (`moi`): hiện popup + lưu `prompt.md` thành `_ticket-moi.md`
  ngay trong thư mục này để OMP đọc.
- Thấy `xong`: popup báo hết việc, vòng lặp kết thúc.
- OMP báo `xong-cho-duyet`: không popup — Muse tự review qua cron 30 phút rồi.

## Cài đặt (làm 1 lần)

1. Trên máy nhà: `git pull origin phieu-viec/rag-fix1` để lấy file mới trong
   `docs/phieu-viec/mailbox/`.
2. Chạy thử 1 lần: chuột phải `Watch-Mailbox.ps1` → Run with PowerShell.
   Nếu bị chặn, mở PowerShell và chạy:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
   rồi chạy lại bước 2.
3. Tự chạy mỗi khi mở máy: nhấn Win+R → gõ `shell:startup` → Enter →
   tạo shortcut trỏ tới `Watch-Mailbox.ps1`.

## Khi popup hiện

Nói với OMP một câu: "đọc mailbox, có ticket mới" (hoặc bảo nó đọc file
`_ticket-moi.md` trong `docs/phieu-viec/mailbox/`).

## Vòng khép kín

Muse viết ticket (`moi`) → watcher popup → OMP làm (`dang-lam` →
`xong-cho-duyet`) → Muse review (cron 30 phút, báo verdict trong chat) →
ĐẠT → Muse viết ticket tiếp (`moi`) … cho đến khi Muse đặt trạng thái
`xong` thì dừng hẳn.

## Tùy chỉnh

- Muốn quét mỗi 60 giây thay vì 90: tạo token fine-grained (quyền
  Contents: read là đủ), mở script, bỏ comment dòng `$token = ...` và dán
  token vào. Không commit token lên git.
- File `watcher_state.json` / `watcher.log` là trạng thái và log của script,
  không cần commit.
