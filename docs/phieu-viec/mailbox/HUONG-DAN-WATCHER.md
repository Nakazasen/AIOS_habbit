# Watcher Windows — tự động nhắc OMP khi có ticket mailbox mới (v2)

## Nó làm gì

Script `Watch-Mailbox.ps1` chạy nền trên máy Windows, mỗi ~90 giây đọc
`docs/phieu-viec/mailbox/trang-thai.md` trên GitHub:

- Thấy ticket mới (`moi`): hiện popup + lưu `prompt.md` thành `_ticket-moi.md`
  ngay trong thư mục này để OMP đọc.
- Ticket `moi` quá 15 phút không ai nhận: popup nhắc lại ("nhắc OMP git pull
  và đọc mailbox").
- OMP báo `xong-cho-duyet`: popup báo ngay — Muse poll mỗi 5 phút sẽ review
  ngay, không phải chờ lâu.
- `dang-lam` quá 20 phút không tiến triển (ghi_chu/commit đứng yên): popup
  cảnh báo "có vẻ kẹt — kiểm tra terminal OMP".
- Thấy `xong`: popup báo hết việc, vòng lặp kết thúc.

Không còn giới hạn cứng 30 phút: mọi thứ chạy theo sự kiện thay đổi trạng
thái, không theo đồng hồ cố định.

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

- "ticket mới" → nói với OMP một câu: "đọc mailbox, có ticket mới" (hoặc bảo
  nó đọc file `_ticket-moi.md` trong `docs/phieu-viec/mailbox/`).
- "ticket treo" → OMP chưa nhận việc, nhắc nó `git pull` rồi đọc mailbox.
- "có vẻ kẹt" → mở terminal OMP xem đang làm gì / có báo lỗi không.
- "OMP báo xong" → không cần làm gì, chờ Muse review (chậm nhất ~5 phút).

## Quy ước cho OMP (để watcher canh được)

- Nhận ticket: đặt `trang-thai.md` thành `dang-lam` NGAY, kèm `ghi_chu` có
  timestamp (giờ máy).
- Mỗi mốc quan trọng (init xong, chạy xong batch/câu hỏi, verify xong):
  cập nhật `ghi_chu` + timestamp trong `trang-thai.md` rồi push.
- Watcher coi "không đổi ghi_chu/commit quá 20 phút" là kẹt và báo động.

## Tùy chỉnh

- Muốn quét mỗi 60 giây thay vì 90: tạo token fine-grained (quyền
  Contents: read là đủ), mở script, bỏ comment dòng `$token = ...` và dán
  token vào. Không commit token lên git.
- Đổi ngưỡng: `$moiWarnMinutes` (mặc định 15), `$stuckMinutes` (mặc định 20).
- File `watcher_state.json` / `watcher.log` là trạng thái và log của script,
  không cần commit.
