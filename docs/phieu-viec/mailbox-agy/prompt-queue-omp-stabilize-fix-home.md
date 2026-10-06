# VÉ: OMP-STABILIZE-FIX-HOME (sửa các lỗi trong fix chống zombie của vé OMP-STABILIZE-HOME)

- Mã vé: `OMP-STABILIZE-FIX-HOME`
- Role OMP gợi ý: DEFAULT (sửa PowerShell + test trên máy thật)
- Máy: nhà h410asrock
- Báo cáo: bổ sung vào `docs/phieu-viec/ket-qua/omp-stabilize-home.md` (mục fix follow-up)

## Bối cảnh — verdict CHƯA ĐẠT vé OMP-STABILIZE-HOME

Pha 1 (điều tra nguyên nhân gốc) được CHẤP NHẬN: tái hiện cô lập có số liệu thật
(thoát sạch 3,67s / treo >70s khi có daemon con / `--max-time 8` tự thoát 8,52s),
xác định 2 nguyên nhân gốc có bằng chứng. KHÔNG cần làm lại Pha 1.

Pha 2 (fix) KHÔNG ĐẠT — kiểm chứng độc lập code thật `docs/phieu-viec/mailbox/Watch-Mailbox.ps1`
(commit `eadeb824`, file 678 dòng) cho thấy 4 điểm lệch so với báo cáo:

1. **Hàm không tồn tại**: dòng 392 gọi `Stop-WorkerTree -pidsToStop $zpids -reason ...`
   nhưng trong toàn bộ file KHÔNG có `function Stop-WorkerTree` (grep: 0 định nghĩa,
   1 chỗ gọi). Runtime sẽ lỗi "not recognized".
2. **Dead code**: `$EnableZombieCleanup` (dòng 383 `if (...)`) và `$DoneGraceMinutes`
   (dòng 388) không được khai báo/gán ở bất kỳ đâu trong file (param block chỉ có
   MailboxDir/Worker/AgyModel/OpenCodeModel) → khối cleanup hậu hoàn thành không bao
   giờ chạy. Chú ý `$ErrorActionPreference = "SilentlyContinue"` nên lỗi bị nuốt im lặng.
3. **Tầng 1 không có trong code**: báo cáo ghi "tự động thêm cờ `--max-time 3600`
   vào `$ompLaunchArgs`" — code thật vẫn là `'-p --auto-approve "{0}"'`, không có
   `--max-time` ở bất kỳ đâu trong file.
4. **Tầng 3 không có trong code**: nhánh `$isNewTicket` (dòng 486-487) chỉ copy prompt
   + popup, không có hành động dọn thợ cũ khi có vé mới.

Bằng chứng test 4.2/4.3 trong báo cáo chạy `taskkill` thủ công + mô phỏng logic rời rạc —
chưa chạy qua đường code thật của watcher (đường đó đang chết theo điểm 1-2).

## Việc cần làm

1. **Định nghĩa `function Stop-WorkerTree`** trong `Watch-Mailbox.ps1` (đặt gần các
   function tiện ích khác): nhận `-pidsToStop` (mảng PID) và `-reason` (string);
   với mỗi PID chạy `taskkill /PID <PID> /T /F` dọn sạch cây tiến trình (gồm daemon
   con/sidecar); `Write-Log` trước/sau mỗi PID; không throw khi PID đã thoát
   (try/catch như code cũ ở dòng 608).
2. **Khai báo và gán giá trị** `$EnableZombieCleanup = $true` và `$DoneGraceMinutes = 2`
   (đúng như báo cáo đã viết) — đặt trong vùng cấu hình đầu file (không nhất thiết
   param, nhưng phải có giá trị trước khi khối dòng 382-397 chạy). Giữ khả năng tắt
   nhanh bằng cờ khi cần.
3. **Thêm `--max-time 3600` vào lệnh khởi chạy omp** (đúng Tầng 1 trong báo cáo):
   chỉ áp cho lane omp; giữ nguyên các lane khác. Đã có bằng chứng Probe C
   (`--max-time 8` thoát sạch 8,52s) nên flag này an toàn.
4. **Implement New Ticket Zombie Override thật**: khi có vé mới (`$isNewTicket`) mà
   process thợ cũ vẫn còn sống NHƯNG CPU và I/O đứng yên (dùng `Get-WorkerCpu`/
   `Get-WorkerIO` có sẵn) → gọi `Stop-WorkerTree` dọn thợ cũ rồi mới mở thợ mới.
   Nếu đánh giá thấy cơ chế zombie-kill cũ (dang-lam im >20 phút) đã đủ → ghi rõ
   lý do chính đáng vào báo cáo thay vì implement, CẤM để báo cáo và code lệch nhau.
5. **Test qua ĐƯỜNG CODE THẬT của watcher** (cấm test mô phỏng rời rạc):
   - Parse-check: file phải load được bằng PowerShell không lỗi
     (vd `[System.Management.Automation.PowerShell]::Create().AddScript([IO.File]::ReadAllText($file))` rồi check errors).
   - Mô phỏng: đặt mailbox ở trạng thái `xong-cho-duyet` + một process giả còn sống
     (vd `ping -t`), chạy đoạn logic cleanup của script và CHỨNG MINH process giả
     bị kill thật (tasklist trước/sau). Ghi terminal output thật vào báo cáo.
6. **File live**: báo cáo mục 5.1 ghi file chạy thực tế là
   `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1` (khác file trong repo). Kiểm tra
   xem file live đã bị thay bằng bản lỗi chưa — nếu có thì cập nhật bản sửa vào đó,
   giữ nguyên backup `.bak_pre_omp_stabilize`.

## Rào cứng (kế thừa vé gốc)

- Mọi thay đổi vào `Watch-Mailbox.ps1` (script chung 3 thợ) test cô lập trước,
  KHÔNG làm gián đoạn watcher đang chạy của OMP/opencode (watcher load script lúc
  khởi động — thay file không ảnh hưởng process đang chạy, nhưng xác nhận lại trước
  khi restart watcher).
- KHÔNG đụng file OMP đang làm (`trend_alerts.py` + test của vé SMA-IMPROVE-HOME)
  — luật 1 file 1 đứa. KHÔNG đụng process thợ đang chạy. Không merge `main`.
  Không secret trong báo cáo/log.
- Heartbeat: mỗi bước ghi 1 dòng `ghi_chu` mốc bước vào mailbox, tối thiểu 15 phút/lần.

## Tiêu chí nghiệm thu

- ĐẠT = 4 điểm lệch trên đều được sửa trong code thật + bằng chứng test qua đường
  code thật (process giả bị kill thật, parse không lỗi) + báo cáo bổ sung phần
  fix follow-up + commit riêng trên branch `phieu-viec/rag-fix1`, không merge `main`.
- Đặc biệt: sau vé này, báo cáo và code PHẢI khớp nhau từng điểm — không còn cảnh
  báo cáo viết một đằng, code một nẻo.
