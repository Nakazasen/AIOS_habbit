# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `dang-lam`
- `ghi_chu`: 2026-10-06 21:24 +07 — Hoàn thành Pha 2: Triển khai 3 tầng bảo vệ chống thợ zombie vào Watch-Mailbox.ps1 (cờ trần thời gian --max-time 60m cho omp -p, cơ chế dọn dẹp hậu hoàn thành Post-Completion Zombie Cleanup sau 2 phút ân hạn, và cơ chế New Ticket Zombie Override khi có vé mới); test cô lập xác nhận dừng sạch 100% cả cây tiến trình qua taskkill /T /F. Bắt đầu Pha 3: Soạn thảo báo cáo chi tiết và kiểm tra cổng chất lượng.
- `ghi_chu`: 2026-10-06 21:22 +07 — Hoàn thành Pha 1: Tái hiện cô lập xác nhận omp -p chạy bình thường thoát sạch trong 3.67s (Exit Code 0); xác định 2 nguyên nhân gốc gây zombie 5.5h (Bun event loop bị daemon con giữ mở khiến waitForAdvisorCatchup kẹt vô hạn + watcher thiếu cơ chế dọn thợ zombie sau khi báo xong-cho-duyet). Bắt đầu Pha 2: thiết kế cơ chế dọn thợ zombie post-completion và cờ bảo vệ cho watcher.
- `ghi_chu`: 2026-10-06 21:19 +07 — Nhận vé OMP-STABILIZE-HOME, kiểm cổng gate: cổng MỞ (lệnh trực tiếp từ user, không vướng cổng SMA-IMPROVE-HOME). Bắt đầu Pha 1: điều tra cô lập nguyên nhân omp -p zombie, kế thừa phát hiện từ omp-exit-probe-home.md và triển khai cơ chế đảm bảo thoát sạch ở tầng launcher/watcher.
- `ghi_chu` (điều phối Muse): 2026-10-06 ~21:20 +07 — [LỆNH TRỰC TIẾP CỦA USER] Phát hành vé `OMP-STABILIZE-HOME`: điều tra vì sao thợ chính OMP zombie đêm 05→06/10 (xong việc không thoát, án ngữ vé mới 5,5 tiếng, user phải kill tay) + fix cho ổn định. Vé này thay thế `OMP-EXIT-PROBE-HOME` (chưa chạy) — gộp điều tra + fix trong một vé. Gỡ cờ `cho-muse` (19:54) theo lệnh user; `FIX-J1CSV-FIXTURE-HOME` trả về hàng chờ #1, giữ nguyên cổng gate (chỉ bắt đầu sau khi mailbox OMP verdict ĐẠT `SMA-IMPROVE-HOME`). Prompt: `docs/phieu-viec/mailbox-agy/prompt-queue-omp-stabilize-home.md`. Role gợi ý: DEFAULT.

- Ticket hiện tại: `OMP-STABILIZE-HOME` — [NHÀ] điều tra zombie thợ chính OMP + fix cho ổn định. Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: DEFAULT.
- `hang-cho`:
  1. `FIX-J1CSV-FIXTURE-HOME` — [NHÀ] cập nhật fixture test JIG theo cổng SMA(20) mới (CỔNG GATE: chỉ bắt đầu sau khi mailbox OMP verdict ĐẠT `SMA-IMPROVE-HOME` — đọc mục 0 trong prompt trước khi làm).

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `cho-muse`
- `ghi_chu` (verdict Muse): 2026-10-06 ~06:33 +07 — **ĐẠT** vé `AUDIT-BUOC2-JIG-HOME`. Kiểm chứng độc lập qua GitHub API: commit `f794051` single-parent, chỉ +159/-0 báo cáo `audit-buoc2-jig-home.md`, không code, không merge `main`; commit `2faccf2` chỉ +4/-1 `trang-thai.md`; đủ 5 tiêu chí vé — (1) 8 chức năng Bước 1 liệt kê đủ; (2) mỗi chức năng có bằng chứng test + dữ liệu thật (tên test/báo cáo); (3) loại trừ cổng SMA(20) đúng rào; (4) 6 việc Bước 2 xếp P0/P1/P2 kèm ước lượng độ lớn; (5) báo cáo đúng path. Điểm phát hiện `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` đối chiếu độc lập khớp mã nguồn trên nhánh (fixture 1 điểm 99.9 trên nền 20 điểm 10.0). Không secret. Cổng compileall/audit/import là self-report của thợ, chấp nhận vì vé không đụng code.
- `ghi_chu` (điều phối Muse): 2026-10-06 ~06:33 +07 — Phát hành vé `FIX-J1CSV-FIXTURE-HOME` (luật hàng chờ không cạn; P0 #2 từ chính báo cáo audit): cập nhật fixture test JIG cho đúng cổng SMA(20) mới. CÓ CỔNG GATE: chỉ bắt đầu sau khi mailbox (OMP) verdict ĐẠT `SMA-IMPROVE-HOME` — đọc mục 0 trong prompt trước khi làm. Prompt: `docs/phieu-viec/mailbox-agy/prompt-queue-fix-j1csv-fixture-home.md`. Role gợi ý: DEFAULT.
- `ghi_chu`: 2026-10-06 19:54 +07 — **CỔNG GATE: đủ 4 lần watcher tự mở agy liên tiếp (~10 phút/lần) mà điều kiện mở vẫn CHƯA có (chờ OMP xong SMA-IMPROVE-HOME có verdict Muse ĐẠT) → đặt `cho-muse` + DỪNG, không quay no-op.** Chuỗi kiểm cổng: lần 1 (06:38) → lần 2 (06:46) → lần 3 (06:51) → lần 4 (19:54). Kiểm tra mailbox OMP (`docs/phieu-viec/mailbox/trang-thai.md`): vé SMA-IMPROVE-HOME vẫn ở trạng thái `dang-lam`, chưa có verdict ĐẠT từ Muse. Theo đúng quy ước và chỉ đạo gate check: dừng chờ Muse điều phối / OMP hoàn tất.
- `ghi_chu`: 2026-10-06 06:51 +07 — kiểm cổng gate lần 3: chờ OMP xong SMA-IMPROVE-HOME (OMP đang đo log thật + viết báo cáo, chưa có verdict Muse ĐẠT), chưa đủ điều kiện bắt đầu; giữ nguyên Trạng thái: `moi`, dừng chờ vòng watcher kế tiếp (3/4 lần).
- `ghi_chu`: 2026-10-06 06:46 +07 — kiểm cổng gate lần 2: chờ OMP xong SMA-IMPROVE-HOME (OMP vừa xong mốc code 06:45, đang đo log thật + viết báo cáo, chưa có verdict Muse ĐẠT), chưa đủ điều kiện bắt đầu; giữ nguyên Trạng thái: `moi`, dừng chờ vòng watcher kế tiếp (2/4 lần).
- `ghi_chu`: 2026-10-06 06:38 +07 — kiểm cổng gate lần 1: chờ OMP xong SMA-IMPROVE-HOME (mailbox OMP hiện đang dang-lam, chưa có verdict Muse ĐẠT), chưa đủ điều kiện bắt đầu; giữ nguyên Trạng thái: `moi`, dừng chờ vòng watcher kế tiếp (1/4 lần).

- Ticket hiện tại: `FIX-J1CSV-FIXTURE-HOME` — [NHÀ] cập nhật fixture test JIG theo cổng SMA(20) mới (chờ OMP xong SMA-IMPROVE mới bắt đầu). Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: DEFAULT.
- `hang-cho`: (trống)

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong-cho-duyet`
- `bao_cao`: `docs/phieu-viec/ket-qua/audit-buoc2-jig-home.md`
- `commit`: `f794051`
- `ghi_chu`: 2026-10-06 06:24 +07 — Hoàn thành 100% vé AUDIT-BUOC2-JIG-HOME: 1) Rà soát toàn bộ 8 chức năng Bước 1 theo kế hoạch công ty 30/09, đối chiếu đầy đủ mã nguồn, bộ test tự động và bằng chứng chạy trên dữ liệu thật (LSU Sub CSV 24,4MB và Master CSV 132 dòng); 2) Tuân thủ rào cứng loại trừ cổng SMA(20) do OMP đang sửa; 3) Phát hiện 1 điểm lệch test cũ test_j1_csv.py do cổng gate SMA(20) chặn vi phạm đơn điểm; 4) Chốt danh sách 6 việc còn thiếu cho Bước 2 (hạn 15/10) xếp theo độ gấp và độ lớn; 5) Lập báo cáo docs/phieu-viec/ket-qua/audit-buoc2-jig-home.md; 6) Cổng kiểm tra: compileall PASS, cli audit status PASS, import app IMPORT_OK, diff src/tests rỗng. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-06 06:23 +07 — Đã rà soát xong 8 chức năng Bước 1 tool JIG theo kế hoạch 30/09 và chạy đối chiếu test/bằng chứng dữ liệu thật; phát hiện 1 lệch test cũ trong test_j1_csv.py do cổng SMA(20) chặn vi phạm đơn điểm; đang tổng hợp danh sách việc Bước 2 và lập báo cáo audit-buoc2-jig-home.md.
- `ghi_chu`: 2026-10-06 06:20 +07 — Nhận vé AUDIT-BUOC2-JIG-HOME, kiểm cổng gate: cổng MỞ (vé mới `moi`). Bắt đầu rà soát readiness Bước 2 tool JIG (chỉ đọc, không sửa code): đối chiếu 8 chức năng Bước 1 theo kế hoạch công ty 30/09 với mã nguồn, test và dữ liệu thật; loại trừ cổng SMA(20) theo yêu cầu.
- `ghi_chu` (verdict Muse): 2026-10-06 ~06:30 +07 — **ĐẠT** vé `SMA-WARMUP-LABEL-HOME`. Kiểm chứng độc lập: commit `4f07d73` single-parent, 6 file (báo cáo +142, i18n +3, jig_alert_cards +50, jig_chat_wire +31/-1, workspace_chat_ui +4, test +77), KHÔNG đụng `trend_alerts.py` đúng luật 1-file-1-đứa với OMP, không merge `main`; đủ 4 tiêu chí vé — (1) nhãn "Đang tích lũy dữ liệu nền (N/20 điểm)" khi N<20; (2) tự ẩn khi N>=20; (3) i18n đủ 3 ngôn ngữ (key `jig_instant_card_warmup` ×3); (4) test 17/17 xanh (chạy lại độc lập trên VM: 17 passed), py_compile sạch. Thợ làm xong trong 6 phút (06:06→06:12).
- `ghi_chu` (điều phối Muse): 2026-10-06 ~06:30 +07 — Phát hành vé `AUDIT-BUOC2-JIG-HOME` (luật hàng chờ không cạn): rà soát readiness Bước 2 tool JIG (hạn 15/10) — liệt kê chức năng nào đã xong/còn thiếu, LOẠI TRỪ cổng SMA(20) vì OMP đang sửa. Chỉ đọc, không code. Prompt: `docs/phieu-viec/mailbox-agy/prompt-queue-audit-buoc2-jig-home.md`. Role gợi ý: PLAN.

- Ticket hiện tại: `AUDIT-BUOC2-JIG-HOME` — [NHÀ] rà soát readiness Bước 2 (hạn 15/10). Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: PLAN.
- `hang-cho`: (trống)

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong-cho-duyet`
- `bao_cao`: `docs/phieu-viec/ket-qua/sma-warmup-label-home.md`
- `commit`: `4f07d73`
- `ghi_chu`: 2026-10-06 06:12 +07 — Hoàn thành 100% vé SMA-WARMUP-LABEL-HOME: 1) Thêm nhãn "Đang tích lũy dữ liệu nền (N/20 điểm) — chưa đủ cơ sở kết luận xu hướng." khi chuỗi < 20 điểm trên thẻ kiểm tra (jig_alert_cards.py, jig_chat_wire.py, workspace_chat_ui.py); 2) Tự động ẩn nhãn khi N >= 20 điểm; 3) Chuỗi nhãn tích hợp qua i18n key jig_instant_card_warmup đủ 3 ngôn ngữ (vi, ja, zh-CN); 4) Tuân thủ rào cứng 1 file 1 đứa: hoàn toàn KHÔNG đụng vào trend_alerts.py; 5) Viết test case bao phủ N=0, N=5, N=20, N=25, routing decide_jig_action, key parity i18n trong test_jig_chat_wire.py (17/17 test passed); 6) Báo cáo docs/phieu-viec/ket-qua/sma-warmup-label-home.md kèm text render mẫu thực tế; 7) Cổng kiểm tra: compileall PASS, cli audit status PASS, import app IMPORT_OK. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-06 06:06 +07 — Nhận vé SMA-WARMUP-LABEL-HOME, kiểm cổng gate: cổng MỞ (lần mở 1/4, vé mới moi, prompt SMA-WARMUP-LABEL-HOME hợp lệ). Bắt đầu kiểm tra codebase jig_chat_wire.py / jig_alert_cards.py để triển khai nhãn warmup N/20 điểm.
- `ghi_chu` (verdict Muse): 2026-10-06 ~06:25 +07 — **ĐẠT** vé `SMA-GATE-REALDATA-HOME`. Kiểm chứng độc lập: commit `271b90d` single-parent, chỉ +161/-0 báo cáo `sma-gate-realdata-home.md` +5176/-0 JSON dữ liệu, KHÔNG sửa `src/` đúng yêu cầu vé, không merge `main`; đủ 4 mục vé — (1) nạp CSV thật 132 dòng đúng path; (2) chạy SMA(20)+gate trên 3 chỉ số; (3) 21/21 vi phạm đơn điểm bị chặn 100%, 0 cảnh báo giả; (4) khảo sát k=1.0–4.0 + giải mã hiện tượng `nen_phang_nhung_lech` (sigma=0 do cảm biến làm tròn). Điểm cộng lớn: phát hiện thật có giá trị (58/62 điểm Nhiệt độ bất thường là giả do sigma=0) + 3 đề xuất cụ thể cho Bước 2 (deadband, k linh hoạt, warmup).
- `ghi_chu` (điều phối Muse): 2026-10-06 ~06:25 +07 — Phát hành vé `SMA-WARMUP-LABEL-HOME` (luật hàng chờ không cạn; song song với OMP làm `SMA-IMPROVE-HOME`, chia file theo luật 1-file-1-đứa): nhãn "Đang tích lũy dữ liệu nền (N/20 điểm)" trên thẻ kiểm tra khi chuỗi <20 điểm. Prompt: `docs/phieu-viec/mailbox-agy/prompt-queue-sma-warmup-label-home.md`. Role gợi ý: DEFAULT.

- Ticket hiện tại: `SMA-WARMUP-LABEL-HOME` — [NHÀ] nhãn warmup N/20 trên thẻ kiểm tra. Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: DEFAULT.
- `hang-cho`: (trống)

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong-cho-duyet`
- `bao_cao`: `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md`
- `commit`: `271b90d`
- `ghi_chu`: 2026-10-06 06:03 +07 — Hoàn thành 100% vé SMA-GATE-REALDATA-HOME: 1) Nạp thành công tệp CSV log JIG thật 2026_08_Master.csv (132 dòng, 677 cột) tại C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\; 2) Chạy chuỗi SMA(20) và cổng gate_canh_bao_theo_xu_huong trên 3 chỉ số Độ ẩm, TaktTime, Nhiệt độ; 3) Đối chiếu xác nhận 21/21 (100%) vi phạm đơn điểm được cổng gate chặn thành công, 0 cảnh báo xu hướng giả; 4) Khảo sát độ nhạy k từ 1.0 đến 4.0 và giải mã hiện tượng nền phẳng nen_phang_nhung_lech do làm tròn cảm biến; 5) Đề xuất 3 cải tiến cụ thể cho Bước 2 (bổ sung deadband, k linh hoạt, warmup); 6) Cổng kiểm tra: compileall PASS, cli audit status PASS, import workspace_chat_app IMPORT_OK, py_compile sạch. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-06 06:00 +07 — Đã hoàn thành chạy phân tích thực nghiệm trên 132 dòng log JIG thật 2026_08_Master.csv: đối chiếu 21/21 vi phạm đơn điểm (11 Độ ẩm, 8 TaktTime, 2 Nhiệt độ) đều được cổng gate chặn thành công 100% (tránh báo sai đơn lẻ); khảo sát độ nhạy k từ 1.0 đến 4.0; đang soạn thảo báo cáo sma-gate-realdata-home.md.
- `ghi_chu`: 2026-10-06 05:58 +07 — Nhận vé SMA-GATE-REALDATA-HOME, kiểm cổng gate: cổng MỞ (lần mở 1/4, vé mới moi, prompt SMA-GATE-REALDATA-HOME hợp lệ). Đã định vị chính xác file dữ liệu thật C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\2026_08_Master.csv (132 dòng dữ liệu). Bắt đầu phân tích chuỗi SMA(20) và đối chiếu cổng gate.
- `ghi_chu` (verdict Muse): 2026-10-06 ~06:05 +07 — **ĐẠT** vé `OMP-EXIT-PROBE-HOME`. Kiểm chứng độc lập: commit `d918a1b` single-parent, chỉ +162/-0 báo cáo `omp-exit-probe-home.md`, không code, không secret, không merge `main`; đủ 3 tiêu chí vé — (1) tái hiện 5 probe cô lập: 2 dạng kẹt (startup do readPipedInput thiếu EOF stdin; shutdown do daemon nền giữ event loop) + 2 lần thoát sạch 9s/16s Exit Code 0; (2) xác định 3 điểm kẹt có dẫn chứng (sidecar PID 15332 ở phiên F1 đêm 05/10, `strictWithoutDeadline: true` trong waitForAdvisorCatchup, readPipedInput khi headless); (3) 4 đề xuất thoát sạch, không đụng code watcher/omp đúng yêu cầu vé. Bảng đối chứng F1 (kẹt 5,5h) vs F2/F3 (thoát 75ms/13ms, có `Session exit recorded`) khớp sự cố thực tế. Lưu ý: phần giải mã binary (offset hàm Bun) là self-report, không kiểm độc lập được từ VM — nhưng kết luận không phụ thuộc vào đó (bằng chứng hành vi từ probe đủ vững).
- `ghi_chu` (điều phối Muse): 2026-10-06 ~06:05 +07 — Phát hành vé `SMA-GATE-REALDATA-HOME` ngay sau verdict (luật hàng chờ không cạn): kiểm chứng cổng cảnh báo xu hướng SMA(20) trên log JIG thật (phục vụ Bước 2 lộ trình tool JIG, hạn 15/10). Prompt: `docs/phieu-viec/mailbox-agy/prompt-queue-sma-gate-realdata-home.md`. Role gợi ý: DEFAULT. `hang-cho` agy trống.

- Ticket hiện tại: `SMA-GATE-REALDATA-HOME` — [NHÀ] kiểm chứng cổng SMA(20) trên log JIG thật (đo chất lượng cảnh báo cho Bước 2). Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role gợi ý: DEFAULT.
- `hang-cho`: (trống)

# Trạng thái mailbox-agy (thợ agy — model gemini-3.8-flash-high, việc khó chuyển claude-sonnet/opus-5.5-medium)

- Trạng thái: `xong-cho-duyet`
- `bao_cao`: `docs/phieu-viec/ket-qua/omp-exit-probe-home.md`
- `commit`: `d918a1b`
- `ghi_chu`: 2026-10-06 05:48 +07 — Hoàn thành 100% vé OMP-EXIT-PROBE-HOME: 1) Tái hiện cô lập thành công 2 dạng kẹt (kẹt startup do readPipedInput thiếu EOF stdin và kẹt shutdown do background daemon giữ event loop); 2) Xác thực thực nghiệm omp -p thoát sạch trong 9s–16s với Exit Code 0 khi không có daemon nền và stdin có EOF; 3) Trích xuất chính xác mã nguồn Bun bên trong omp.exe (hàm runPrintMode/Cnp và cơ chế waitForAdvisorCatchup với strictWithoutDeadline: true); 4) Lập bảng đối chứng 3 phiên F1 kẹt vs F2/F3 thoát; 5) Đề xuất 4 giải pháp thoát sạch triệt để (không đụng code watcher/omp); 6) Dọn sạch thư mục tạm C:\temp\omp_probe*; 7) Cổng kiểm tra: compileall PASS, cli audit status PASS, import app IMPORT_OK. Đang chờ Muse duyệt.
- `ghi_chu`: 2026-10-06 05:36 +07 — Nhận vé OMP-EXIT-PROBE-HOME, kiểm cổng gate: cổng MỞ (lần mở 1/4, vé mới moi, prompt OMP-EXIT-PROBE-HOME hợp lệ). Bắt đầu điều tra cô lập nguyên nhân omp -p không thoát sau khi xong việc.
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
