# Báo cáo vé WATCHER-UPGRADE-PC0575 — nâng cấp vòng lặp mailbox PC0575

- Máy: KDTVN-PC0575 (thợ opencode, opencode CLI v2.0.22).
- Thời gian: 2026-10-06 22:27–22:35 +07.
- Phạm vi: `D:\Sandbox\agent-mailbox` (nhánh `main`), không đụng `config.local.ps1` (đã gitignore), không đụng watcher/process OMP.

## Đã làm

1. Pull code mới: `git fetch origin` rồi `git pull --rebase origin main`. Kết quả fast-forward `132e2c8..e202c10`, không conflict.
2. Đối chiếu 4 commit vé yêu cầu đều có: zombie v2 `5fa86d7`, chọn template theo major `dbf23c4`, remote-access `d1c9dbb`, chống mù chữ BOM `e202c10`.
3. Kiểm code mới: đọc đoạn chọn template theo major — máy v2 giữ `--standalone --model --auto`, máy v1 giữ `--auto --dir --attach`, không gộp. `max-time` blanket đã gỡ (chỉ còn dòng chú thích cấm dùng lại). Guard BOM chỉ kiểm `Watch-Mailbox.ps1`, file này còn đủ BOM.
4. Kiểm cấu hình: `config.local.ps1` khớp `where` (omp/agy/opencode), token đã có, file đã nằm trong `.gitignore` nên không commit.
5. Nạp code mới: chỉ restart watcher opencode (kill PID 30592 code cũ, mở lại PID 28984 code mới qua `MailboxWatcher-opencode`). Watcher OMP (PID 868) đang chạy vé `LSU-QUALITY-PC0575` nên giữ nguyên, không đụng. Mailbox `mailbox-pc0575-agy` tồn tại nên không cần báo điều phối tạo.

## Kết quả nghiệm thu

- [x] `Parser::ParseFile` 0 lỗi mọi `.ps1`; BOM `EF-BB-BF` đủ (trừ `config.local.ps1` là ASCII không dấu, guard BOM không kiểm file này nên watcher vẫn chạy).
- [x] 1 vé opencode chạy thật: log có `LAUNCH` lúc `22:24:28` cho vé này; process thợ PID 19496 đúng mẫu v2 `--standalone --model opencode/muse-spark-1.3-contributor-free --auto`, không cờ lạ, sống từ 22:24 đến 22:32 (khoảng 8 phút).
- [x] Watcher poll tươi: opencode `updated 22:31:49` trạng thái `dang-lam` (thấy thợ đang làm nên không mở trùng); OMP `updated 22:32:02` trạng thái `dang-lam`. Watcher agy không chạy vì mailbox agy đã `xong` từ 15:57. Không có `loi:`/`UNKNOWN-STATUS`/`BOM-CHECK-FAIL` mới trong 3 log watcher.
- [x] `git status` trong `agent-mailbox` sạch; không force-push, không merge bừa, không commit `config.local.ps1`.

## Bằng chứng (lệnh + output thật)

- `git log --oneline -8` sau pull: `e202c10` (BOM), `cd29f1a` (fix agy), `132e2c8` (đo lại major sau config), `d1c9dbb` (remote-access), `5fa86d7` (zombie v2), `dbf23c4` (template theo major).
- Log opencode: `[2026-10-06T22:24:28] LAUNCH [opencode] 1/4 ticket=WATCHER-UPGRADE-PC0575 ...`.
- Process thợ: `opencode.exe run "<ticket>" --standalone --model opencode/muse-spark-1.3-contributor-free --auto` (PID 19496).
- Trạng thái watcher mới: `watcher_state-mailbox-pc0575-opencode-opencode.json` ghi `updated 22:31:49`, `status dang-lam`.
- OMP còn sống: process PID 868 vẫn chạy, CPU khoảng 113,9.

## Ghi chú

- File `QUY-UOC.md` riêng trong `mailbox-pc0575-opencode` chưa có nên dùng tạm `mailbox-opencode/QUY-UOC.md` (giống vé trước).
- Cổng gate watcher: lần mở này là lần 1 (22:24), chưa chạm ngưỡng 4 lần nên mở vé bình thường, không đặt `cho-muse`.
