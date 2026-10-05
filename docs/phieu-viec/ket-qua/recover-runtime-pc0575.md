# Báo cáo vé `RECOVER-RUNTIME-PC0575` — khôi phục dữ liệu runtime production đã mất

- Máy: `KDTVN-PC0575` (Windows 11 Pro build `10.0.26200` x64, **CPU-only**), user `kdtvn\tvn183660` — **KHÔNG thuộc nhóm Administrators**.
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md`; nhánh `phieu-viec/rag-fix1`.
- Thời gian thực hiện: 2026-10-05 ~16:18–16:42 +07 (các mốc đã push: `18a26a8` nhận vé → `5c6c2c0` Bước 1 → `7cd89ae` Bước 2+4).
- **Verdict: KHÔNG KHÔI PHỤC ĐƯỢC → `cho-muse`.** Không tìm thấy bản index production `e54c7745…` (2.842.415.104 B) ở bất kỳ đâu trên máy; cây model `local_runs\retrieval_models\bge-m3-5617a9f` cũng đã mất (có đường tải/ghép lại — mục 4).
- Không xoá/ghi gì vào dữ liệu hiện có; không đụng `C:\AIOS_p5\library.sqlite.bak-20260930`; không tải model (đúng vé).

## 0. Cổng gate (vòng watcher)

- Watcher PC0575 (`D:\Sandbox\agent-mailbox\`) tự mở OMP `LAUNCH [omp] 1/4` lúc **16:16:08** cho vé này (`launchStallCount=1`) — **chưa tới ngưỡng "4 lần watcher"**; vé không có điều kiện mở riêng → OMP nhận vé làm trực tiếp, không quay no-op.
- Đặt `trang-thai.md` = `dang-lam` + push ngay khi nhận (`18a26a8`), cập nhật tiến độ từng mốc (`5c6c2c0`, `7cd89ae`).

## 1. Bước 1 — Recycle Bin ổ C và ổ D

Cách làm: parse metadata `$I` (đường dẫn gốc + dung lượng + thời điểm xoá) của `$Recycle.Bin` trên cả 2 ổ, script `local_runs/dieu_tra/recover-pc0575/scan_recycle_bin.py` (chỉ đọc).

- `C:\$Recycle.Bin\S-1-5-21-2780589664-2521333910-3044434614-4077` (SID của user hiện tại): 20 file `$I` + `desktop.ini`; toàn bộ là rác cũ **18/08/2020 → 06/10/2022** (2 mục ~8,5 MB + 18 CSV vài trăm byte), **tất cả payload `$R` đều không còn**; không mục nào tên chứa `sqlite` / `bge-m3` / `retrieval_models` / `workspace_chat` / `local_runs`.
- `D:\$Recycle.Bin\S-1-5-21-…-4077`: 1 file `$I` (PDF `D:\SETUP\tvn183660\desktop\…` xoá 11/10/2021) — không payload.
- 12 thư mục SID khác (System `S-1-5-18`, `…-500` Administrator, `…-1786`, `…-4084`, `…-4131`, `…-5105`, `…-5147`, `…-6694`): **`ACCESS DENIED`** — không đọc được vì user không thuộc Administrators (kiểm chéo: `net localgroup Administrators` chỉ có Administrator / Domain Admins / kyocera; `whoami /groups` không có S-1-5-32-544).

**Kết luận Bước 1:** bản xoá sáng nay **không nằm trong Recycle Bin** (bin của user không có mục nào mới; khả năng: xoá bỏ qua bin kiểu Shift+Delete / công cụ dọn dẹp, hoặc bị dọn khỏi bin). Hạn chế: không kiểm được bin của các SID khác (cần quyền admin/IT).

## 2. Bước 2 — Antivirus / quarantine

- Trung tâm bảo mật Windows: **CrowdStrike Falcon Sensor** (đang chạy: service `csagent` + `CSFalconService` = Running) + Windows Defender.
- **Windows Defender đang tắt** (`Get-MpComputerStatus`: `AMServiceEnabled=False`, `AntivirusEnabled=False`; `Get-MpPreference` lỗi `0x800106ba`; event log Defender không có sự kiện 1116/1117/1006/1015) → **không có quarantine Defender nào** để kiểm; thư mục `C:\ProgramData\Microsoft\Windows Defender\Quarantine` truy cập bị từ chối (không cần thiết vì service tắt).
- CrowdStrike: `C:\ProgramData\CrowdStrike` chỉ có `QuarantineReleaseRemovableMedia` + `ZeroTrustAssessment` (16/09/2026); danh sách cách ly của Falcon do console/SOC công ty quản, user thường không đọc được.
- **Kết luận Bước 2:** không có dấu vết cách ly trên máy. Muốn loại trừ 100% khả năng Falcon cách ly file sáng nay phải hỏi IT kiểm console (ghi chú, không chặn vé).

## 3. Bước 3 — Quét toàn máy tìm bản copy index

Phạm vi: 2 ổ cố định duy nhất **C: + D:** (không có USB/ổ ngoài cắm — kiểm `Get-Volume`); script `local_runs/dieu_tra/recover-pc0575/scan_sqlite.py` (chỉ đọc), log + JSON cùng thư mục (local-only, không commit).

- Đã quét **1.536.807 file** (C: 1.264.036 + D: 272.771); lỗi truy cập 440 (thư mục hệ thống) — không ảnh hưởng kết luận.
- Có **726 file** chứa `.sqlite` trong tên; **chỉ 1 file ≥ 1 GB**:

| Path | Size (byte) | SHA-256 (8 đầu) | Đối chiếu |
|---|---:|---|---|
| `C:\AIOS_p5\library.sqlite.bak-20260930` | 2.552.659.968 | `062ec090` | ⚠ backup cũ 29–30/09 — **KHÔNG phải** bản production `e54c7745` |

- Các path từng chứa index: `C:\AIOS_workspace_chat_rag_v2_production\` → không tồn tại; `C:\AIOS_habit_index_ve03\` → không tồn tại; `C:\AIOS_p5\` → chỉ có file backup trên.
- Quét thêm (profile user + ổ D:) file tải dở / nén / backup ≥500 MB (`*.crdownload`, `*.part`, `*.zip`, `*.7z`, `*.rar`, `*.tar`, `*.gz`, `*.bak`) → **0 hit**; `Downloads` không tồn tại; Desktop trống; máy **không** có ổ Google Drive sync.
- Audit hiện trạng (chạy lại trong phiên, chỉ đọc): `uv run --no-sync --group dev python -B -m aios_habit.workspace_chat_rag_v2_deployment` → `Status: FAIL` / `deployment_model_unavailable` (đúng trạng thái đã ghi 15:32 hôm nay).

**Kết luận Bước 3:** **không có bản index production `e54c7745…`** (2.842.415.104 B) trên máy dưới bất kỳ dạng nào.

## 4. Bước 4 — Khả năng tải lại model (chỉ kiểm tra, chưa tải)

- Model đích: `BAAI/bge-m3` @ `5617a9f61b028005a4858fdac845db406aefb181` (nguồn: `src/aios_habit/bge_m3_manifest.json` — checksum cây gói `b1d887e0…`; manifest máy `config/workspace_chat_rag_v2.local.json` trỏ `D:/Sandbox/AIOS_habbit/local_runs/retrieval_models/bge-m3-5617a9f` + checksum `697a97c3…`, cả hai đều nằm trong danh sách được duyệt của deployment).
- **Kết nối Hugging Face: được** — `https://huggingface.co` HTTP 200; API revision trả đúng sha `5617a9f…`.
- **Tải thử byte-exact (2 file nhỏ):**
  - `config.json` 687 B → SHA-256 khớp manifest (`26159e7a…`).
  - `sparse_linear.pt` 3.516 B → SHA-256 khớp manifest (`45c93804…`).
  - Probe dải byte file lớn (`pytorch_model.bin`): HTTP 206, 1 MiB đầu ~0,7 MB/s (lượt đầu), 16 MiB ~9,3 MB/s.
- **Dung lượng:** 12 file gói gốc ≈ 2.295 GB (2,14 GiB); cả repo (30 file, gồm `onnx/` + `imgs/` + README) ≈ 4.587 GB (4,27 GiB). Cây `bge-m3-5617a9f` trên PC0575 (checksum được duyệt `697a97c3…`) gồm **30 file — trùng số file với snapshot HF** ⇒ có khả năng ghép lại đúng byte từ HF, **nhưng phải verify `sha256_model_tree` sau khi tải** (chưa tải trong vé này).
- **Lưu ý quan trọng:** cây ONNX đã nghiệm thu cho đường chạy `models/bge-m3-onnx-fp32` (`sha256:9f81075f…`, 2.289.625.694 B, 9 file) **không** khớp `onnx/` có sẵn trên HF (bản HF: `model.onnx_data` 2.266.820.608 B ≠ bản export 2.266.886.160 B) → nguồn đúng là zip `bge-m3-onnx-fp32.zip` (1.326.939.447 B) trên Drive AIOS_Data (đã verify ẩn danh 30/09) hoặc cây trên máy nhà `h410asrock`.

## 5. Bước 5 — Verdict + danh sách nguồn còn lại

**Verdict: KHÔNG KHÔI PHỤC ĐƯỢC** → đặt `trang-thai.md` = `cho-muse`, dừng (không quay no-op).

Danh sách **mọi nguồn còn lại trên máy** (đã kiểm đủ 2 ổ C+D, không có USB):

| # | Nguồn | Đường dẫn | Dung lượng | Ghi chú |
|---|---|---|---|---|
| 1 | Backup cũ 30/09 | `C:\AIOS_p5\library.sqlite.bak-20260930` | 2.552.659.968 B (SHA `062ec090`) | Bản 29–30/09, **KHÔNG phải production**; vé cấm dùng thay & cấm đụng |
| 2 | Rác test canary | `local_runs\workspace_chat_rag_v2_canary\workspace_chat.sqlite` | nhỏ | Do test tạo 15:14 hôm nay, không phải dữ liệu thật |
| 3 | Model base | Hugging Face `BAAI/bge-m3` @ `5617a9f…` | ≈ 2,30 GB (gói gốc) | Tải được, đã verify byte-exact 2 file (mục 4) |
| 4 | Cây ONNX nghiệm thu | zip `bge-m3-onnx-fp32.zip` trên Drive AIOS_Data (1.326.939.447 B) hoặc máy nhà `models/bge-m3-onnx-fp32` (9 file, 2.289.625.694 B, `9f81075f…`) | — | Không nằm trên PC0575 |
| 5 | Index production `e54c7745…` | **không tồn tại trên máy** (C+D, mọi điểm từng chứa) | — | Cần nguồn ngoài PC0575 nếu muốn khôi phục đúng bản |

**Hạn chế đã gặp:** (a) Recycle Bin của các SID tài khoản khác cần quyền admin/IT mới đọc được; (b) Falcon quarantine cần IT kiểm console; (c) phần model ONNX cần nguồn ngoài máy (Drive/máy nhà).

**Đề xuất hướng tiếp theo (Muse/user quyết):**
1. Kiểm nguồn copy-deploy **bên ngoài PC0575** (máy nhà / Drive / nơi deploy gốc) để khôi phục đúng bản `e54c7745…` — giữ nguyên giá trị mọi số đo cũ.
2. Nếu không có nguồn nào: dùng tạm backup 30/09 (chỉ khi có lệnh Muse; chênh dữ liệu sau 30/09) hoặc rebuild index — đều là vé riêng, theo quy ước dry-run/backup.
3. Model: tải lại base từ HF + lấy cây ONNX từ zip Drive/máy nhà, verify `sha256_model_tree` trước khi dùng.
