# Vé WATCHER-UPGRADE-PC0575 — Nâng cấp vòng lặp mailbox lên code mới nhất

**Máy thực hiện:** CÔNG TY KDTVN-PC0575 (thợ opencode).
**Phạm vi:** `D:\Sandbox\agent-mailbox` (repo vòng lặp mailbox), `config.local.ps1`, watcher đã đăng ký.
**CẤM:** force-push, merge commit bừa, commit `config.local.ps1` (chứa token), bịa mailbox không tồn tại.

Bạn đang ngồi trên máy công ty PC0575 (user tvn183660, không admin). Nhiệm vụ: nâng cấp vòng lặp mailbox lên code mới nhất, kiểm chứng thợ chạy được, rồi báo cáo. Bên máy nhà vừa đẩy một loạt vá quyết định — máy này đang chạy code cũ từ chiều 05/10, thiếu hết. Làm theo thứ tự, vướng thì tự điều tra đến gốc, không báo PASS giả.

## 1. Pull code mới (cẩn thận, 2 bên cùng đẩy main)
1. Trong `D:\Sandbox\agent-mailbox`: `git fetch origin` xem trước, rồi `git pull --rebase origin main`. Có conflict thì DỪNG, hỏi user — cấm force-push, cấm merge commit bừa.
2. Xác nhận có các commit mới: `zombie v2`, `chong mu chu BOM`, `chon template theo major CLI`, `remote-access`. Liệt kê `git log --oneline -8` làm bằng chứng.

## 2. Những gì đã đổi (đọc để khỏi giẫm chân)
- Watcher giờ tự nhận major CLI opencode: máy này v2 → giữ nguyên đường `--standalone --model --auto` của bên này (không đổi hành vi); máy nhà v1 → đường `--auto --dir --attach`. Đừng gộp 2 đường làm một.
- CẤM thêm lại `--max-time` blanket: đã gỡ vì nó giết cả vé dài chạy thật (KNOWLEDGE 6 tiếng). Diệt zombie đã có cơ chế chính xác (im + CPU+I/O phẳng mới kill).
- File `.ps1` LUÔN lưu UTF-8 có BOM (máy Shift-JIS đọc sai regex tiếng Việt nếu mất BOM — vừa cháy 1 lần). Watcher mới tự kiểm BOM lúc khởi động, mất là dừng + báo.
- Có thêm `Install-RemoteAccess.ps1` (server điều khiển từ xa, chưa cần thì thôi).

## 3. Cấu hình + nạp
1. `config.local.ps1` đã có sau Mot-Lan: kiểm tra đường dẫn omp/agy/opencode bằng `where`, sai thì sửa. Dán token GitHub user đưa vào `$token`, lưu. KHÔNG commit file này.
2. Chỉ đăng ký thợ đã cài trên máy: `where agy`, `opencode --version`. Thiếu thì chạy `-Workers omp` thôi, đừng đăng ký thợ ma.
3. Restart toàn bộ watcher đang chạy (kill process → Start task) cho nạp code mới. Watcher nào chưa có mailbox tương ứng (`mailbox-pc0575-agy`) thì báo điều phối tạo, đừng tự bịa mailbox.

## 4. Nghiệm thu (báo đúng mẫu)
- [ ] `[Parser]::ParseFile` 0 lỗi mọi .ps1; BOM còn (3 byte đầu `EF-BB-BF`).
- [ ] 1 vé opencode test chạy thật: log có `LAUNCH`, process thợ sống >2 phút (đúng template v2, không cờ lạ).
- [ ] 3 watcher (hoặc số thợ đã đăng ký) poll tươi: `watcher_state*.json` có `updated` mới, không `loi:`/`UNKNOWN-STATUS` mới trong log.
- [ ] `git status` sạch. Báo cáo: làm gì / thấy gì / bằng chứng (lệnh + output thật).

**Lưu ý:** OMP trên máy này đang chạy vé `LSU-QUALITY-PC0575` (lane RAG đo tiếp từ checkpoint). KHÔNG đụng process/vé của OMP, không restart watcher omp giữa chừng đo.
