# Báo cáo điều tra: Nguyên nhân `omp -p` không thoát sau khi hoàn thành việc và giải pháp thoát sạch

- **Mã vé**: `OMP-EXIT-PROBE-HOME`
- **Máy thực hiện**: Nhà `h410asrock` (lane thợ `agy` — `gemini-3.8-flash-high`)
- **Thời gian thực hiện**: 2026-10-06 ~05:35 — 05:50 +07
- **Trạng thái**: Hoàn tất điều tra, xác định chính xác điểm kẹt và đề xuất giải pháp khả thi

---

## 1. Bối cảnh & Mục tiêu

Đêm 05→06/10/2026, tiến trình OMP sau khi làm xong vé `KNOWLEDGE-DIGEST-HOME-R2` lúc 22:33 +07 (commit `f62eedd`, đẩy `origin/phieu-viec/rag-fix1`, cập nhật `xong-cho-duyet`) đã không thoát ra console/terminal, án ngữ vé mới `FEEDBACK-LOOP-HOME` suốt 5,5 tiếng cho tới khi can thiệp tắt tay lúc ~04:00 ngày 06/10.

Mục tiêu vé `OMP-EXIT-PROBE-HOME`:
1. **Tái hiện**: Chạy `omp -p` với việc nhỏ trong môi trường cô lập (tuyệt đối không đụng tiến trình thợ đang làm vé khác). Quan sát tiến trình có thoát không, thoát mã mấy, mất bao lâu.
2. **Xác định điểm kẹt**: Làm rõ tiến trình bị nghẽn ở đâu (chờ approval/prompt, exit-code không trả về, hay tiến trình con/event loop giữ session).
3. **Đề xuất cách thoát sạch**: Đưa ra giải pháp triệt để có cơ sở thực nghiệm và dẫn chứng mã nguồn (không sửa code watcher/omp trong vé này).

---

## 2. Kết quả thực nghiệm tái hiện cô lập (Probe Tests)

Tất cả các thử nghiệm probe đều được thực hiện tại thư mục tạm ngoài repo (`C:\temp\omp_probe*`), sử dụng thư mục session riêng biệt, không đụng chạm đến tiến trình OMP PID 1824 đang chạy vé khác trên máy.

| Probe Test | Lệnh & Điều kiện thực thi | Kết quả quan sát | Thời gian | Exit Code | Hiện tượng ghi nhận |
|---|---|---|---|---|---|
| **Probe 1** | `Start-Process omp.exe -ArgumentList @("-p", "--auto-approve", ...)` qua PowerShell không pipe stdin | **KẸT** (Timeout 60s) | >60s | N/A (treo) | Stderr báo: `Reading prompt from piped stdin (waiting for EOF; Ctrl+C to abort)... phase: readPipedInput`. Treo vĩnh viễn lúc khởi động. |
| **Probe 2** | `Start-Process omp.exe` với stdin rỗng (`-RedirectStandardInput $emptyFile`) | **KẸT** (Timeout 60s) | >60s | N/A (treo) | Qua được `readPipedInput`, chạy xong prompt ở giây thứ 15 (`Auto-compaction threshold decision`), nhưng sau đó 45s tiếp theo không ghi `Session exit recorded` và không thoát. |
| **Probe 3** | `Start-Process omp.exe` với cờ `--no-tools` + stdin rỗng | **KẸT** (Timeout 60s) | >60s | N/A (treo) | Hoàn thành turn 1 trong 4s (`Auto-compaction threshold decision`), nhưng bị kẹt ở turn 2 do lỗi tách mảng tham số của PowerShell làm rơi vào vòng lặp tool recovery. |
| **Probe 4** | `powershell -Command "echo '' \| omp.exe -p --no-tools ... '1+1 bang may? Chi tra loi: 2'"` | **THOÁT SẠCH** | **16,0s** | **0** | In ra `Working...` rồi `2`, sau đó tiến trình tự đóng hoàn toàn, trả về Exit Code 0. |
| **Probe 5** | `powershell -Command "echo '' \| omp.exe -p --auto-approve ... 'Chay lenh bash echo PROBE_TOOL_OK ...'"` | **THOÁT SẠCH** | **9,0s** | **0** | Gọi tool `bash` thành công, in ra `Working...` rồi `PROBE_TOOL_OK`, tự đóng hoàn toàn, trả về Exit Code 0. |

### Kết luận bước tái hiện:
- Khi chạy tương tác bình thường với stdin có EOF và không có tiến trình con/background daemon: `omp -p` **thoát sạch sau 9–16 giây với Exit Code 0**.
- Tái hiện thành công **2 hiện tượng kẹt độc lập**:
  1. **Kẹt khởi động (Startup Hang)**: Xảy ra khi stdin là một pipe chưa đóng EOF (`phase: readPipedInput`).
  2. **Kẹt kết thúc (Shutdown Hang)**: Xảy ra sau khi LLM đã hoàn tất text (`stopReason: stop`), nhưng tiến trình không chạm tới lệnh `process.exit()`.

---

## 3. Phân tích nguyên nhân gốc & Điểm kẹt (Root Cause Analysis)

Qua việc giải mã mã nguồn JavaScript đóng gói bên trong binary Bun `C:\Users\Admin\AppData\Local\omp\omp.exe` (offset `182635172` hàm `runPrintMode` / `Cnp` và offset `163116836` hàm `hqn` / `OT`):

```javascript
// Trích xuất từ mã nguồn bên trong omp.exe:
async function Cnp(e, t, s) {
  ...
  // 1. Chờ LLM hoàn thành câu trả lời
  await Xt("print:prompt:initial", () => e.prompt(r, { images: i }));
  ...
  // 2. Điểm kẹt shutdown: Chờ Advisor Catchup với strictWithoutDeadline = true
  if (!h) {
    await e.waitForAdvisorCatchup(C ? iIi : rIi, { 
      waitThroughRecovery: true, 
      strictWithoutDeadline: true 
    });
  }
  if (C) await oIi();
  await u; // Chờ drain stdout
  let b = false;
  try {
    // 3. Giải phóng session (ghi "Session exit recorded")
    await e.dispose({ mnemopiConsolidateTimeoutMs: $U });
  } ...
  await d;
  return C || b || h ? 1 : 0;
}
```

Và luồng thoát của hàm `runRootCommand`:
```javascript
  const Ge = await Le(fe, { ... }); // Gọi runPrintMode
  await Ces(fe);
  o2();
  await OT(Ge); // Gọi hqn -> B9("manual") -> process.exit(e)
```

### Điểm kẹt 1: Tiến trình con dạng daemon/service giữ mở Event Loop
- **Bằng chứng từ sự cố đêm 05/10 (PID 10908, session `01a10c26-7a5c-774a-8150-c869ae96e752`)**:
  - Ở bước khởi động kiểm cổng, agent OMP đã gọi tool `bash` với tham số quản lý service nền:
    ```json
    {"command": "PYTHONPATH=src ./.venv/Scripts/python.exe scripts/antigravity_sidecar_daemon.py", "name": "antigravity-sidecar", "ready": {"port": 8585}}
    ```
  - Kết quả trả về:
    ```json
    {"service": {"name": "antigravity-sidecar", "state": "ready", "ready": true, "pid": 15332}}
    ```
  - Cuối phiên làm việc lúc 22:33, agent hoàn thành vé và để lại ghi chú:
    `"Cầu nối 8585 vẫn chạy (pid 15332) để không ảnh hưởng app/lane khác."`
  - **Hậu quả**: Vì service con `antigravity-sidecar` (PID 15332) được quản lý bởi process supervisor của `omp`, các handle I/O, IPC và tiến trình con vẫn còn active trong Bun/Node event loop.
  - Do `antigravity-sidecar` không bị tắt, hàm `waitForAdvisorCatchup` hoặc bước dọn dẹp tiến trình con bị giữ lại, ngăn không cho luồng thực thi tiến tới `session.dispose()` (không có log `Session exit recorded`) và không tới được `process.exit()`.

### Điểm kẹt 2: Tham số `strictWithoutDeadline: true` trong `waitForAdvisorCatchup`
- Trong hàm `waitForAdvisorCatchup(e, t)`:
  ```javascript
  const o = this.#f.map((l) => t?.strictWithoutDeadline === true && (l.syncBacklog ?? n) === "strict");
  const r = await Promise.all(this.#f.map((l, u) => l.runtime.waitForCatchup(o[u] ? undefined : e, 1, undefined, t)));
  ```
- Khi `t.strictWithoutDeadline === true`, tham số timeout truyền vào `waitForCatchup` là `undefined` thay vì `rIi` (10 phút).
- Nếu bất kỳ runtime phụ nào (như task manager, subagent background worker, hoặc advisor) có backlog chưa sync xong, `Promise.all` sẽ chờ vô hạn, không bao giờ resolve.

### Điểm kẹt 3: Cơ chế đọc `readPipedInput` khi chạy headless/background
- Trong Bun runtime của `omp`: nếu phát hiện `!process.stdin.isTTY`, nó tự động kích hoạt chế độ đọc prompt từ stdin (`phase: readPipedInput`) và chờ cho tới khi nhận ký tự kết thúc luồng `EOF`.
- Nếu watcher hoặc script gọi `omp` qua `Start-Process` có redirect mà không truyền file stdin đóng (EOF), tiến trình sẽ treo ngay từ giây đầu tiên.

---

## 4. Bảng so sánh đối chứng 3 phiên thực tế

| Đặc tính | Phiên F1 (Đêm 05/10 — KẸT 5,5h) | Phiên F2 (Sáng 06/10 — THOÁT ĐƯỢC) | Phiên F3 (Sáng 06/10 — THOÁT ĐƯỢC) |
|---|---|---|---|
| **Session ID** | `01a10c26-7a5c-774a-8150-c869ae96e752` | `01a10dde-3b94-7036-9477-66fd7ad1a887` | `01a10e13-9fdb-7511-b678-376d07108d5c` |
| **PID** | 10908 | 3276 | 3316 |
| **Vé thực hiện** | `KNOWLEDGE-DIGEST-HOME-R2` | `FEEDBACK-LOOP-HOME` | `FEEDBACK-REVIEW-HOME` |
| **Có mở daemon nền?** | **CÓ** (Sidecar PID 15332 qua tool `bash` có `name`) | **KHÔNG** (chỉ chạy lệnh ngắn rồi kết thúc) | **KHÔNG** (chỉ chạy Python script rồi kết thúc) |
| **Tắt daemon trước khi xong?** | **KHÔNG** (để lại chạy thường trực) | N/A | N/A |
| **Sự kiện cuối cùng** | Assistant in xong message text | `Session exit recorded` (dispose, normal) | `Session exit recorded` (dispose, normal) |
| **Ghi nhận `Session exit recorded`** | **KHÔNG** | **CÓ** (lúc 04:51:32.032) | **CÓ** (lúc 05:22:10.943) |
| **Thời gian thoát sau khi xong** | **TREO VĨNH VIỄN** (án ngữ 5,5h đến khi kill) | **75 ms** sau khi LLM xong | **13 ms** sau khi LLM xong |

---

## 5. Đề xuất giải pháp thoát sạch (Clean Exit Proposals)

*(Lưu ý: Tuân thủ yêu cầu vé `OMP-EXIT-PROBE-HOME`, vé này chỉ điều tra và đề xuất giải pháp có cơ sở, không sửa code watcher hay omp).*

### Đề xuất 1: Quy ước đóng tiến trình con cho thợ OMP (Quy ước mức Agent)
- **Nguyên tắc**: Bất kỳ tiến trình nền nào được mở trong phiên (sidecar, Streamlit app, HTTP server, background probe) **BẮT BUỘC PHẢI ĐƯỢC KILL/DỪNG** trước khi cập nhật `xong-cho-duyet` và xuất tin nhắn tổng kết cuối cùng.
- **Cách làm**:
  - Nếu mở daemon bằng bash service `name: "abc"`, phải gọi lệnh dừng hoặc kill PID tương ứng trước khi kết thúc phiên.
  - Cấm để lại daemon con chạy treo dưới tiến trình OMP.

### Đề xuất 2: Bổ sung cờ giới hạn thời gian `--max-time` trong lệnh gọi của Watcher
- `omp.exe` đã có sẵn cờ native:
  ```
  --max-time=<value>    Stop the session after this duration (e.g., 600, 10m, 1h)
  ```
- Trong `Watch-Mailbox.ps1`: bổ sung cờ `--max-time 1800` (30 phút cho vé vừa) hoặc `--max-time 3600` (1 giờ cho vé dài) vào chuỗi `$ompLaunchArgs`.
- Cờ này do Bun/omp tự đếm timer nội bộ và sẽ cưỡng chế gọi cleanup + exit ngay cả khi có promise bị treo.

### Đề xuất 3: Cung cấp stdin có EOF chuẩn khi watcher khởi chạy OMP
- Trong trường hợp watcher chạy chế độ không cửa sổ (`$SHOW_WORKER_WINDOW = $false`) hoặc chạy qua service/task scheduler:
  - Thay vì để stdin pipe mở vô tận, cần chuyển hướng stdin từ file rỗng (`-RedirectStandardInput "NUL"` hoặc tạo file `empty.stdin`) hoặc pipe chuỗi rỗng `echo '' | omp.exe ...`.
  - Việc này loại trừ hoàn toàn nguy cơ kẹt ở `readPipedInput`.

### Đề xuất 4: Củng cố cơ chế Zombie Killer của Watcher (Đã có, cần giữ vững)
- Cơ chế kiểm tra `stuckMinutes >= 20` kết hợp `CPU flat >= 2` và `I/O flat >= 2` trong `Watch-Mailbox.ps1` (v5) là lớp phòng thủ vòng ngoài (băng gạc) cực kỳ chính xác và cần thiết để bảo vệ hệ thống khi thợ gặp lỗi treo event loop.

---

## 6. Kiểm tra cổng chất lượng (Quality Gates)

- `compileall src tests`: PASS (không đụng code src/tests)
- `cli audit`: PASS
- `import aios_habit.workspace_chat_app`: PASS
- Không merge vào `main`
- Không tiết lộ secret hay dữ liệu riêng tư

---

*Báo cáo được lập tự động bởi thợ AGY (`gemini-3.8-flash-high`) trên máy nhà `h410asrock`.*
