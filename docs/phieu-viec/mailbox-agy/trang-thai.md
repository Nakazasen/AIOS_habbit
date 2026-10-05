# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `moi`
- `ghi_chu` (verdict Muse): 2026-10-06 ~05:45 +07 — **ĐẠT** vé `DRIVE-LINK-RETRY-HOME` (poll 05:42+07). Kiểm chứng độc lập qua GitHub API: commit `e2a5f21` single-parent (d8a86ed), chỉ +36/-0 báo cáo `upload-split-drive-home.md` (section 8 mới) và +4/-1 `trang-thai.md`, không code, không secret, không merge `main`; đủ 4 tiêu chí vé — (1) thử lại 2 link 05:10 & 05:14 ngày 06/10, Drive vẫn chặn, ghi trung thực không bịa, đã bổ sung Folder ID chính xác `dieu_tra_loi` (1MeM7BWGeDO1skAusH6DVrBAOwHvVZrLp) và `lsu` (10gL0Zbwbm1oko7gckrizFUoU8dR0_Yno); (2) 5 file Drive còn nguyên 100% đúng tên + byte size; (3) xóa sạch 5 file `C:\temp\verify_*` (~2,85GB), ổ C 12,73→15,39GB; (4) báo cáo bổ sung section 8 đúng mẫu. Cổng kiểm tra (compileall/cli audit/import app) là self-report của thợ, chấp nhận vì vé không đụng code.
- `ghi_chu` (điều phối Muse): 2026-10-06 ~05:45 +07 — Phát hành vé `OMP-EXIT-PROBE-HOME` theo đúng thứ tự `hang-cho` #1 sau verdict (chữa gốc vụ zombie 5,5 tiếng: điều tra vì sao `omp -p` xong việc không thoát; tái hiện + xác định điểm kẹt + đề xuất thoát sạch; cấm sửa code watcher/omp trong vé này). Quy ước chuẩn mới đã có sẵn trong mẫu vé (heartbeat mốc bước tối thiểu 15p/lần + checkpoint/resume bắt buộc). `hang-cho` agy rỗng. Watchdog sẽ dựng watcher trong ~10 phút.

- Ticket hiện tại: `OMP-EXIT-PROBE-HOME` — [NHÀ] điều tra vì sao `omp -p` xong việc không thoát (chữa gốc zombie 5,5 tiếng). Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: DEFAULT.
- `hang-cho`: (trống)

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong-cho-duyet`
- `bao_cao`: `docs/phieu-viec/ket-qua/upload-split-drive-home.md`
- `commit`: 122cf3c
- `ghi_chu`: 2026-10-06 05:30 +07 — Hoàn thành 100% các tiêu chí vé DRIVE-LINK-RETRY-HOME: 1) Thử lấy share link/ID cho 2 file lớn, Drive vẫn chưa cho chia sẻ lúc 05:10 & 05:14 ngày 06/10 (ghi nhận trung thực, tuyệt đối không bịa link/ID ảo; đã cập nhật bổ sung Folder ID chính xác của dieu_tra_loi 1MeM7BWGeDO1skAusH6DVrBAOwHvVZrLp và lsu 10gL0Zbwbm1oko7gckrizFUoU8dR0_Yno); 2) Xác nhận 5 file trên Drive nguyên vẹn 100% đúng tên và byte size so với báo cáo ban đầu; 3) Đã xóa sạch 5 file tạm C:\temp\verify_* (~2,85GB), ổ C tăng từ 12.73GB lên 15.39GB; 4) Bổ sung section 8 vào báo cáo kết quả; 5) Cổng kiểm tra: compileall PASS, cli audit status PASS, import workspace_chat_app IMPORT_OK. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-06 04:29 +07 — Nhận vé DRIVE-LINK-RETRY-HOME: bắt đầu kiểm tra Drive lấy 2 link chia sẻ còn thiếu (LSU, Dieu-tra-loi), xác nhận 5 file còn nguyên và dọn dẹp file tạm C:\temp\verify_*.
- `ghi_chu` (điều phối Muse): 2026-10-06 ~04:25 +07 — Phát hành vé `DRIVE-LINK-RETRY-HOME` (prompt mới `prompt-queue-drive-link-retry-home.md`): lấy nốt 2 link chia sẻ Drive còn thiếu (LSU, Dieu-tra-loi), xác nhận 5 file còn nguyên, xóa file tạm C:\temp\verify_* (~2,8GB). Role gợi ý: SMOL.

- Ticket hiện tại: `DRIVE-LINK-RETRY-HOME` — [NHÀ] lấy nốt 2 link chia sẻ Drive + dọn file tạm verify. Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: SMOL.
- `hang-cho`: 1. `OMP-EXIT-PROBE-HOME` → `prompt-queue-omp-exit-probe-home.md` (điều tra vì sao omp -p xong việc không thoát; phát hành tự động sau verdict vé hiện tại)
- `ghi_chu` (điều phối Muse): 2026-10-06 ~04:40 +07 — Xếp hàng vé `OMP-EXIT-PROBE-HOME` (chữa gốc vụ zombie 5,5 tiếng). Áp quy ước chuẩn mới trong mẫu vé: heartbeat mốc bước tối thiểu 15 phút/lần + checkpoint/resume bắt buộc vé dài.

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong`
- `ghi_chu`: 2026-10-05 20:58 +07 — **Verdict Muse: ĐẠT** vé `SCAN-O-D` (poll 20:44+07): đủ 3 tiêu chí — cây thư mục + dung lượng (§2), bảng sqlite đường dẫn/SHA/size (§4), đề xuất dọn 4 mức có thứ tự (§7). Đối chiếu độc lập: SHA báo cáo khớp ghim production `45eb0e07…65b7c0` và bản đông `062ec090…4ef8ca`; commit f7836c5 chỉ chạm file báo cáo, phương pháp quét chỉ đọc. Lưu ý: SHA chi tiết 593 file sqlite tạm pytest + 13 file cache eval lưu ở CSV/hồ sơ đính kèm ngoài báo cáo (chấp nhận vì là file tạm; toàn bộ SHA kho production/backup/split đã inline). Không có vé xếp hàng tiếp cho agy → đóng mailbox ở `xong`, chờ phân công mới.

- Ticket hiện tại: `SCAN-O-D` — [NHÀ] kiểm kê ổ D chỉ đọc (cây thư mục, SHA sqlite, đề xuất dọn — không thực hiện). Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: SMOL. Không ghi/xóa ổ D.
- `hang-cho`: chưa có
- `commit`: f7836c5
- `bao_cao`: `docs/phieu-viec/ket-qua/scan-o-d.md`
- `ghi_chu`: 2026-10-05 20:17 +07 — Hoàn thành 100% vé SCAN-O-D: kiểm kê toàn diện ổ D chỉ đọc, đầy đủ SHA-256 các file sqlite, đối chiếu khớp kho production và bản đông, đề xuất dọn dẹp 4 mức an toàn, chất lượng audit PASS. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-05 06:27 +07 — Đã quét xong cây thư mục cấp 1-2 ổ D và hoàn tất tính SHA-256 cho toàn bộ file sqlite trong D:\Sandbox; đang đối chiếu kho production máy nhà và lập báo cáo scan-o-d.md.
- `ghi_chu`: 2026-10-04 ~23:35 +07 — Verdict Muse ĐẠT: báo cáo `don-o-c-may-nha.md` đủ bằng chứng từng bước (B0: .codex 2.49GB + .gemini 4.30GB + opencode 60.46MB; B1: C:\tmp 41.76MB; B4: xóa backup pre-merge 30.95MB sau integrity_check bản giữ lại ok); không đụng ổ D/index production/model ONNX/session opencode; mục tiêu 5-8GB đạt (free đo thật 7.33GB). Không có vé xếp hàng tiếp cho agy → đóng mailbox ở `xong`, chờ phân công mới.
- `ghi_chu`: 2026-10-04 23:32 +07 — Hoàn thành vé DON-O-C-AGY: thu hồi thực tế +6.23GB (free tăng từ 1.10GB lên 7.33GB, đạt mục tiêu 5–8GB). Toàn bộ quality gates và PRAGMA integrity_check PASS. Đang chờ duyệt.
