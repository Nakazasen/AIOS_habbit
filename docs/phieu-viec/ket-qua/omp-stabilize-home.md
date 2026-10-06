# Báo cáo kỹ thuật: Điều tra nguyên nhân thợ chính OMP zombie và giải pháp thoát sạch ổn định

- **Mã vé**: `OMP-STABILIZE-HOME`
- **Máy thực hiện**: Nhà `h410asrock` (lane thợ `agy` — `gemini-3.8-flash-high`)
- **Thời gian thực hiện**: 2026-10-06 ~21:18 — 21:26 +07
- **Trạng thái**: Hoàn tất 100% điều tra, triển khai giải pháp và kiểm chứng thực nghiệm
- **Branch**: `phieu-viec/rag-fix1`

---

## 1. Bối cảnh & Mục tiêu

Đêm 05→06/10/2026, sau khi hoàn thành vé `KNOWLEDGE-DIGEST-HOME-R2` lúc 22:33 +07 (commit `f62eedd`, đẩy `origin/phieu-viec/rag-fix1`, cập nhật `xong-cho-duyet`), tiến trình OMP (`omp.exe -p`, thợ chính PID 10908) đã không thoát khỏi terminal, án ngữ vé mới `FEEDBACK-LOOP-HOME` suốt 5,5 tiếng cho tới khi người dùng can thiệp tắt tay lúc ~04:00 ngày 06/10.

Mục tiêu vé `OMP-STABILIZE-HOME`:
1. **Pha 1 — Điều tra nguyên nhân gốc**: Tái hiện trong phiên probe cô lập (không đụng tiến trình thợ đang làm vé khác), xác định chính xác điểm nghẽn khiến OMP không thoát.
2. **Pha 2 — Fix cho ổn định**: Implement cơ chế đảm bảo thoát sạch ở tầng launcher/watcher (không sửa binary ngoài OMP), có feature flag an toàn, không gián đoạn watcher đang chạy.
3. **Pha 3 — Báo cáo & Bàn giao**: Ghi nhận bằng chứng thực nghiệm, quy trình kiểm thử trước/sau và phương án rollback.

---

## 2. Kết quả điều tra Pha 1: Nguyên nhân gốc

Qua điều tra đối chiếu giữa hành vi thực nghiệm cô lập, log session thực tế đêm 05/10 và mã nguồn JavaScript của Bun runtime bên trong `omp.exe`:

### 2.1. Kết quả thực nghiệm tái hiện cô lập (Probe Tests)

| Probe | Điều kiện chạy | Kết quả | Thời gian | Exit Code | Hiện tượng |
|---|---|---|---|---|---|
| **Probe A (Tiêu chuẩn)** | `omp -p --no-tools` với stdin đóng (EOF) | **THOÁT SẠCH** | **3,67s** | **0** | LLM in text, session dispose, Bun event loop rỗng và process thoát ngay lập tức. |
| **Probe B (Background job)** | Chạy tác vụ con nền (background job/daemon) | **CHỜ ĐỢI** | >70s | N/A | Tiến trình duy trì event loop để chờ job hoàn tất hoặc nhận thông báo async. |
| **Probe C (Trần thời gian)** | `omp -p --max-time 8` | **CƯỠNG CHẾ THOÁT SẠCH** | **8,52s** | **1** | In `Deadline exceeded`, Bun timer cưỡng chế ngắt session và thoát hoàn toàn. |

### 2.2. Điểm kẹt 1: Tiến trình con dạng daemon/service giữ mở Event Loop của Bun (Phía OMP)
- Trong phiên sự cố F1 đêm 05/10 (PID 10908, session `01a10c26-7a5c-774a-8150-c869ae96e752`), thợ OMP đã khởi chạy tool `bash` với tham số service nền:
  ```json
  {"command": "PYTHONPATH=src ./.venv/Scripts/python.exe scripts/antigravity_sidecar_daemon.py", "name": "antigravity-sidecar", "ready": {"port": 8585}}
  ```
  tạo ra tiến trình con `antigravity-sidecar` (PID 15332) chạy thường trực.
- Ở cuối phiên, agent không dừng service này mà để lại chạy tiếp. Bun supervisor của OMP vẫn duy trì các open handle, IPC pipe và socket kết nối với daemon con này.
- Trong mã nguồn `Cnp` bên trong `omp.exe`:
  ```javascript
  if (!h) {
    await e.waitForAdvisorCatchup(C ? iIi : rIi, { 
      waitThroughRecovery: true, 
      strictWithoutDeadline: true 
    });
  }
  ```
  Khi `strictWithoutDeadline: true`, Bun runtime chờ đợi vô hạn và không bao giờ gọi tới `session.dispose()` hay `process.exit()`.

### 2.3. Điểm kẹt 2: Lỗ hổng chuyển tiếp trạng thái trong Watcher (Phía Launcher/Watcher)
- Trong logic cũ của `Watch-Mailbox.ps1`:
  1. Khi thợ báo `xong-cho-duyet`, watcher chỉ popup `"tho bao xong"` rồi giữ nguyên trạng thái theo dõi. Watcher **hoàn toàn không có cơ chế kiểm tra hay dọn dẹp tiến trình thợ sau khi thợ đã báo cáo xong**.
  2. Khi Muse duyệt xong và phát hành vé mới (`status = "moi"`):
     Watcher kiểm tra:
     ```powershell
     if (-not $ompRunning) { Invoke-WorkerLaunch ... }
     else { Show-Popup "Mailbox: ticket moi (tho ban)..." }
     ```
     Vì tiến trình `omp.exe` của vé cũ vẫn còn sống (zombie kẹt event loop), `$ompRunning` là `$true`.
  3. Watcher kết luận thợ đang bận và **không bao giờ khởi chạy thợ cho vé mới**, trong khi thợ cũ đã dừng mọi tác vụ và không bao giờ đọc lại mailbox.
  4. Hệ thống rơi vào trạng thái bế tắc hoàn toàn suốt 5,5 tiếng cho đến khi user kill tay.

---

## 3. Giải pháp kỹ thuật đã triển khai (Pha 2)

Để giải quyết triệt để vấn đề ở tầng của mình (launcher/watcher) mà không cần can thiệp binary ngoài, giải pháp gồm **3 tầng phòng thủ vững chắc**:

### Tầng 1: Cờ trần thời gian `--max-time` trong lệnh khởi chạy
- Bổ sung tham số `$OmpMaxTimeMinutes = 60` (mặc định 60 phút).
- Khi watcher khởi chạy `omp.exe`, tự động thêm cờ `--max-time 3600` vào `$ompLaunchArgs`.
- Cơ chế timer nội bộ của Bun sẽ tự động ngắt phiên và thoát tiến trình sạch sẽ nếu tác vụ kéo dài quá 1 giờ, ngăn chặn vĩnh viễn việc án ngữ hàng tiếng đồng hồ.

### Tầng 2: Cơ chế dọn dẹp thợ Zombie hậu hoàn thành (`Post-Completion Zombie Cleanup`)
- **Tín hiệu**: Mailbox chuyển sang trạng thái `xong-cho-duyet` hoặc `xong`.
- **Nguyên lý**: Khi thợ đã cập nhật trạng thái này, công việc của vé đã hoàn tất 100%, code và báo cáo đã được commit và push. Thợ không còn lý do gì để tiếp tục chiếm slot.
- **Thời gian ân hạn**: `$DoneGraceMinutes = 2` (2 phút để thợ tự kết thúc và dọn dẹp session).
- **Hành động**: Nếu sau 2 phút mà tiến trình thợ vẫn còn sống, watcher kích hoạt hàm `Stop-WorkerTree`:
  Sử dụng `taskkill /PID <PID> /T /F` để tiêu diệt sạch toàn bộ cây tiến trình (gồm cả daemon con/sidecar/subprocesses nếu có), giải phóng hoàn toàn tài nguyên và slot làm việc.

### Tầng 3: Cơ chế ghi đè thợ Zombie khi có vé mới (`New Ticket Zombie Override`)
- Khi có vé mới (`status = "moi"` và `$isNewTicket = $true`):
- Nếu tiến trình thợ vẫn còn tồn tại nhưng đo đạc thấy CPU và I/O đứng yên (`cpuNow == workerCpu` và `ioNow == workerIO`), watcher nhận diện thợ cũ là zombie sót lại từ phiên trước.
- Watcher tự động gọi `Stop-WorkerTree` dọn dẹp thợ cũ để nhặt vé mới ngay lập tức.

### Feature Flag an toàn
- Biến cờ `$EnableZombieCleanup = $true` được bổ sung vào `param(...)` của `Watch-Mailbox.ps1`.
- Có thể bật/tắt tức thì hoặc cấu hình qua tham số dòng lệnh mà không cần sửa code.

---

## 4. Bằng chứng kiểm thử thực nghiệm (Evidence-Based)

### 4.1. Bằng chứng cờ `--max-time` tự thoát sạch
- **Lệnh chạy**:
  `omp.exe -p --auto-approve --max-time 8 "Dung tool bash chay: sleep 60"`
- **Kết quả thực tế từ terminal**:
  ```text
  ElapsedSeconds : 8.52
  ExitCode       : 1
  Output         : Working...
                   Deadline exceeded
  ```
- **Xác nhận**: Tiến trình tự thoát sạch sau đúng 8,52 giây, không còn tiến trình con nào tồn tại.

### 4.2. Bằng chứng hàm dọn dẹp cây tiến trình `Stop-WorkerTree`
- **Kịch bản**: Khởi tạo tiến trình cha PowerShell spawn cây con CMD và tiến trình con cháu `ping 127.0.0.1 -t`.
- **Kết quả thực tế từ terminal**:
  ```text
  SUCCESS: The process with PID 4104 (child process of PID 7336) has been terminated.
  SUCCESS: The process with PID 16204 (child process of PID 7336) has been terminated.
  SUCCESS: The process with PID 4744 (child process of PID 9916) has been terminated.
  SUCCESS: The process with PID 7336 (child process of PID 9916) has been terminated.
  SUCCESS: The process with PID 9916 (child process of PID 7592) has been terminated.
  ```
- **Xác nhận**: `ChildsAfterCount : 0`, toàn bộ cây tiến trình bị dọn dẹp 100%.

### 4.3. Bằng chứng tích hợp logic Zombie Cleanup
- **Kịch bản**: Giả lập thợ zombie PID 14512 còn sống sau 5 phút ở trạng thái `xong-cho-duyet`.
- **Kết quả thực tế**:
  ```text
  ZombiePid        : 14512
  CleanedTriggered : True
  StillRunning     : False
  Success          : True
  LogContent       : [2026-10-06T21:23:45] POST-DONE-ZOMBIE [test-worker]: Da o trang thai xong-cho-duyet hon 5.0 phut nhung process van con song. Don dep de giai phong slot.
                     [2026-10-06T21:23:45] CLEANUP-WORKER-TREE [test-worker]: Dung PID 14512 (ly do: Post-completion zombie cleanup (xong-cho-duyet 5.0 min))
  ```

---

## 5. Hướng dẫn vận hành & Rollback

### 5.1. Vị trí file triển khai
- File script môi trường chạy thực tế: `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1`
- File quản lý phiên bản trong git repo: `docs/phieu-viec/mailbox/Watch-Mailbox.ps1`

### 5.2. Cách Rollback tức thì
1. **Qua cờ dòng lệnh (không cần sửa file)**:
   Thêm `-EnableZombieCleanup:$false` vào lệnh khởi chạy watcher.
2. **Khôi phục từ bản backup**:
   File backup trước khi sửa đã được lưu tại:
   `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1.bak_pre_omp_stabilize`
   Lệnh khôi phục:
   `Copy-Item "D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1.bak_pre_omp_stabilize" "D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1" -Force`

---

## 6. Kiểm tra các cổng chất lượng (Quality Gates)

- `uv run --no-sync --group dev python -m compileall src tests`: **PASS**
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: **PASS** (`"status": "PASS"`)
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: **PASS** (`IMPORT_OK`)
- Rào 1 file 1 đứa: Hoàn toàn **KHÔNG ĐỤNG** `trend_alerts.py` hay test của vé `SMA-IMPROVE-HOME`.
- Rào an toàn tiến trình: Tiến trình OMP PID 11080 đang chạy vé `SMA-IMPROVE-HOME` không hề bị gián đoạn.
- Không merge vào `main`.
- Không chứa secret hay thông tin nhạy cảm.

---

*Báo cáo được lập tự động bởi thợ AGY (`gemini-3.8-flash-high`) trên máy nhà `h410asrock`.*
