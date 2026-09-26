# Watcher Windows — tự động nhắc/giám sát OMP (v4: vòng lặp cưỡng chế 2 đầu)

## Ý tưởng

- **Đầu 1 (Muse, trên VM):** viết ticket → poll mailbox mỗi 5 phút → review,
  trả verdict. Không có gì mới thì im lặng.
- **Đầu 2 (script này, máy Windows):** poll mailbox mỗi ~90 giây + kiểm tra
  OMP còn sống không (qua tên process), rồi:
  - Ticket `moi` + OMP đang rảnh → popup (hoặc **tự mở OMP** nếu bật
    `$AUTO_LAUNCH`)
  - Ticket `moi` + OMP đang mở nhưng chưa nhận → nhắc nhẹ 1 lần
  - `dang-lam` + thấy process OMP → **im lặng** (đang làm thì thôi)
  - `dang-lam` + không thấy process → cảnh báo (có thể crash giữa chừng)
  - `dang-lam` quá 20 phút không tiến triển → cảnh báo kẹt
  - `xong-cho-duyet` → popup (Muse sẽ review trong ~5 phút)
  - `xong` → **không dừng ngay**: đếm số lần check liên tiếp thấy `xong` ổn
    định (mặc định 3 lần ≈ 4,5 phút, chỉnh bằng `$idleExitChecks`) để loại trừ
    ghi nhầm/thoáng qua, rồi popup **tổng kết** (liệt kê ticket đã xong trong
    đợt) + **tự dừng script**

Người vẫn giữ chốt duyệt: ticket nào cũng "dừng chờ duyệt", Muse hỏi bạn
trong chat trước khi viết ticket tiếp theo.

Lưu ý: `xong-cho-duyet` KHÔNG tính là "hết việc" để dừng — vì có thể đang
chờ bạn duyệt ticket tiếp theo (bạn đi vắng vài tiếng là bình thường).
Script cứ chạy nền nhẹ (1 request GitHub/90s), không tốn gì. Muốn chạy tiếp
sau khi đã tự dừng (Muse mở ticket mới sau này) thì chạy lại script —
shortcut trong `shell:startup` vẫn còn đó.

## Cài đặt (làm 1 lần)

1. Trên máy nhà: `git pull origin phieu-viec/rag-fix1` để lấy file mới trong
   `docs/phieu-viec/mailbox/`.
2. Mở `Watch-Mailbox.ps1`, sửa khối **CẤU HÌNH**:
   - `$ompProcessName`: tên process OMP trong Task Manager > Details
     (không có `.exe`). Mở OMP lên rồi vào Task Manager xem cho chắc.
   - Muốn full tự động: điền `$ompLaunchCommand` + `$ompLaunchArgs` rồi đặt
     `$AUTO_LAUNCH = $true`. **Chỉ làm khi OMP của bạn hỗ trợ chạy kèm prompt
     từ dòng lệnh** (chế độ headless/non-interactive). Không chắc thì để
     `$false` — script chỉ popup nhắc, bạn mở OMP tay.
3. Chạy thử 1 lần: chuột phải `Watch-Mailbox.ps1` → Run with PowerShell.
   Nếu bị chặn: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
4. Tự chạy mỗi khi mở máy: Win+R → `shell:startup` → tạo shortcut tới file.

## Kiểm tra nó canh đúng không

- Mở OMP, để nó làm ticket → script phải im lặng (trừ khi kẹt >20 phút).
- Tắt OMP khi đang `dang-lam` → phải popup "OMP bien mat?".
- Nhờ Muse viết ticket test (`moi`) khi OMP tắt → phải popup "ticket moi
  (OMP ranh)".

## Quy ước cho OMP (để watcher canh được)

- Nhận ticket: đặt `trang-thai.md` thành `dang-lam` NGAY, kèm `ghi_chu` có
  timestamp (giờ máy).
- Mỗi mốc quan trọng: cập nhật `ghi_chu` + timestamp rồi push.

## Tùy chỉnh

- `$pollSeconds` (90), `$moiWarnMinutes` (15), `$stuckMinutes` (20),
  `$idleExitChecks` (3).
- Poll 60 giây: thêm token fine-grained (Contents: read), bỏ comment dòng
  `$token`. Không commit token lên git.
- `watcher_state.json` / `watcher.log`: trạng thái + log, không cần commit.
