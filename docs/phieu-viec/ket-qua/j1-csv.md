# Vé `J1-CSV` — JIG: nhập cả file CSV + chọn biểu đồ, tự gửi mail: kết quả verify trên máy nhà

- Trạng thái: **Verify xong trên dữ liệu thật, chờ Muse duyệt.** Kết luận: **ĐẠT tiêu chí vé** — (1) nhập 1 file CSV log jig thật (24,4 MB, ma trận rộng Iris) bằng đúng lệnh chat; (2) chọn biểu đồ → ra biểu đồ đúng (đủ 3 loại, PNG hợp lệ); (3) bắn cảnh báo test → **mail đính kèm đúng biểu đồ đã setup** (`phan_bo`), cổng duyệt tay giữ nguyên.
- Nhánh: `phieu-viec/rag-fix1`. Chuỗi mốc: `1741780` (phát hành vé 17:49:58) → `8375a5f` (OMP nhận vé 18:08) → `266c889` (mốc 1) → `95de064` (mốc 2) → (mốc 3) → (báo cáo này) → (mốc `xong-cho-duyet` theo sau).
- Mã vé verify: `698ea1a` (Muse code+test trên VM, 6 tệp +916/−9; thông báo `ad0d197` lúc 18:05:58: review độc lập 15/15 + 149/149, AST không vướng PEP 701).
- Máy: Windows 10 Pro `10.0.18363` x64, Python 3.11.14 (`.venv` repo). Ràng buộc giữ: **không đụng DB gốc / ổ D / `main`**; file sinh ở `C:/tmp/j1-verify/` (ngoài repo) + 1 mirror dữ liệu chỉ-đọc trên ổ C; vé **không code** trên máy nhà (chỉ verify, đúng lane [VM]).

## 0. Cổng gate (vòng khép kín)

- Vé phát hành 17:49:58 (lane [VM]). Phiên gate **1/4** (watcher `D:\Sandbox\Vong_lap_giao_viec\` tự mở OMP lúc 17:49:58, `launchStallCount=1`) thấy **chưa có mã J1-CSV, chưa có thông báo** → chỉ ghi 1 dòng tiến độ (`d99d211`), **không đặt `cho-muse`**.
- Trong lúc phiên chạy: Muse push mã `698ea1a` (17:59:20) rồi thông báo chính thức `ad0d197` (18:05:58) → **điều kiện mở ĐÃ TỚI** → OMP nhận vé (`8375a5f`, 18:08) — **không dùng nhánh "4 lần watcher"/`cho-muse`, không quay no-op**.

## 1. Mốc 1 — test vé + nhóm liên quan (máy nhà, Py 3.11.14)

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_j1_csv.py` (chuẩn, từ repo) | **11 đỗ / 4 bỏ qua** — 4 bài cổng dữ liệu thật skip đúng thiết kế vì path hardcode kiểu Linux `/home/hatch/...` |
| như trên, chạy từ cwd ổ C sau khi mirror file thật về đúng path resolve (`C:\home\hatch\...\2ND-1035\IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv`; 24.375.633 B; size + SHA-256 `6ebf293087ed8053a81e3df5a3fc55ab9a72ddac9082ae51fe42369d6578441c` khớp đúng entry trong `C:/tmp/lsu1-deploy/lsu_manifest.json` — manifest bản copy ổ D của vé LSU-1) | **15/15 đỗ** (đủ 4 bài dữ liệu thật: nhập ma trận Iris, nhập lại bỏ qua, file đổi → nhập lại, dòng lẻ 7 cột) |
| Nhóm liên quan đúng bộ Muse nêu — 10 tệp (jig_chat_wire, alert_config, alert_mailer, csv_chart_selector ×2, omnibar ingest, iris archive, iris log_intake, spc_chart, smtp UI) | **149/149 đỗ** (1 lượt sạch) |
| Mở rộng thêm 3 tệp (lsu_iris_data, in_app_risk_alert, agent_conversational_omnibar) | **34/34 đỗ** |

Log: `C:/tmp/j1-verify/j1_ticket_repo.log`, `j1_ticket_mirror.log`, `j1_related149.log`.

## 2. Mốc 2 — E2E dữ liệu thật (đúng đường app)

Run: `C:/tmp/j1-verify/e2e/run-20261001-181644` (script `C:/tmp/j1-verify/e2e_run.py`; luồng đúng app `handle_jig_chat_text` + `alert_mailer`; kèm `summary.json`, 5 PNG, 1 EML).

### 2.1 Nhập cả 1 file CSV log jig thật

- Lệnh chat `nhập tệp log "<path>"` → *"Đã nhập 50,000 giá trị đo từ tệp IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv (ma trận rộng Iris) vào kho log."* — tệp có **1.191.207** giá trị nên chạm trần thiết kế `GIOI_HAN_DONG_MOI_LAN = 50.000` mỗi lần nhập; app báo đúng "chia nhỏ tệp rồi nhập tiếp" (hành vi có sẵn của kho — ghi nhận, không chặn).
- Nhập lại cùng file → *"…đã nhập trước đó và nội dung không đổi, nên hệ thống bỏ qua để tránh ghi trùng."* — chống trùng cấp tệp (sha256 + size + mtime) hoạt động.

### 2.2 Chọn biểu đồ → ra biểu đồ đúng

- `chọn biểu đồ phân bố` → "Đã chọn Phân bố giá trị cho … (áp dụng ngay)" + PNG `bieu_do_phan_bo.png` 51.103 B (PIL mở/verify hợp lệ).
- Vẽ đủ 3 loại từ dữ liệu thật: `xu_huong` 73.372 B / `phan_bo` 51.103 B / `so_sanh_mau` 71.083 B.

### 2.3 Bắn cảnh báo test → mail kèm đúng biểu đồ đã setup

- Cấu hình bằng chat: thêm email `ca-test@nhay.local`; `chọn biểu đồ gửi mail phân bố` + `bỏ biểu đồ gửi mail xu hướng` → `bieu_do_dinh_kem = ['phan_bo']`.
- Dòng test `2026-10-01T10:00:00,61C1068E6222,IrisLSU (log dán),SKEW:BLACK,-1022,um,OK` (nền thật 133 điểm, min −593 / max −374) → kết luận **"Vi phạm"** (EWMA lệch 120,751 > ngưỡng 92,941) → **tự động vẽ đúng Phân bố giá trị** + câu *"Đã tự động vẽ Phân bố giá trị theo cấu hình để đính kèm vào email cảnh báo."* (đúng loại đã setup, không rơi về mặc định).
- Thẻ đề xuất (hàm app `build_de_xuat_mail_data`): tiêu đề `[MÔ PHỎNG] Cảnh báo xu hướng JIG …`, `ten_anh = bieu_do_phan_bo.png`, `co_anh = True`, mã duyệt `DUYET-41DBB996` — chỉ số chưa có giới hạn thật được gắn nhãn minh bạch đúng cơ chế.
- `build_alert_email`: email 71.516 B, part `image/png` tên `bieu_do_phan_bo.png` khớp meta; cổng duyệt tay `can_send_with_approval(proposal, False) = False` / `(…, True) = True` — **không bao giờ gửi lén** (giữ luật CONSTITUTION).

## 3. Mốc 3 — cổng nền + full suite so nền B5

Cổng (log `C:/tmp/j1-verify/gates_j1.log`):

- `compileall -q src tests` → **EXIT=0**
- `python scripts/check_docs.py` → **DOCUMENTATION_CONTRACT=PASS** (exit 0)
- `python -m aios_habit.cli audit` → **`{"status":"PASS"}`**, errors/warnings rỗng
- import `aios_habit.workspace_chat_app` → **OK**
- `git diff --check` / `git diff --cached --check` → sạch; `git status --short` → sạch

Full suite (log `C:/tmp/j1-verify/pytest_full_j1.log`): **3.581 đạt / 6 bỏ qua / 26 lỗi / 9 error** (679,93 s) — so nền B5 home (`3.561/2/35/9`):

- **+20 đạt** = +11 test `test_j1_csv` chạy được ở chế độ chuẩn (4 bài cổng dữ liệu thật skip ở chế độ này — đã đỗ đủ 15/15 ở mốc 1 khi có mirror) **+ 9 test `test_bge_subprocess_*` nền B5 từng fail `bge_worker_init_stdout_eof` nay đỗ** (chạy lại sạch 16/16 trong 3,4 s; nghi do tải lúc nền B5 chạy song song — hướng tốt hơn, xác nhận không phải hồi quy).
- **Node FAILED/ERROR hiện tại (35 mục) = tập con đúng của 44 mục nền B5**: `comm` cho thấy 9 mục biến mất là đúng 9 test bge nói trên (`only_b5.txt`), **0 mục mới phát sinh** (`only_j1.txt` rỗng); 9 error còn lại vẫn là fixture hardcode đường VM `/home/hatch/…` (ngoài phạm vi vé).

## 4. Tiêu chí ĐẠT của vé (đối chiếu)

- [x] **OMP verify: nhập 1 file CSV log jig thật → chọn biểu đồ → ra biểu đồ đúng** — mục 2.1 + 2.2, qua đúng lệnh chat trên dữ liệu thật.
- [x] **Bắn cảnh báo test → mail đi kèm đúng biểu đồ đã setup** — mục 2.3: đúng loại đã cấu hình (`phan_bo`), đính kèm trong email, cổng duyệt tay giữ nguyên.

## 5. Ràng buộc & ghi nhận không chặn

- Không đụng DB gốc / ổ D / `main`; không ghi index; file sinh chỉ ở `C:/tmp/j1-verify/` + mirror chỉ-đọc `C:\home\hatch\...` phục vụ đúng path test; repo chỉ nhận báo cáo + `trang-thai.md`.
- Ghi nhận không chặn: (a) trần `GIOI_HAN_DONG_MOI_LAN=50k` mỗi lần nhập — tệp 24 MB (1.191.207 giá trị) vượt trần ~24 lần, app báo rõ + gợi ý chia nhỏ (thiết kế sẵn của kho, ngoài phạm vi vé); (b) `jig_id` mặc định `IrisLSU (log dán)` khi ma trận không kèm mã JIG — nhãn có sẵn của adapter Iris; (c) chỉ số chưa có giới hạn thật → biểu đồ/mail gắn nhãn `[MÔ PHỎNG]` qua metadata (đúng cơ chế minh bạch của repo).

## 6. Bằng chứng (artifact trên ổ C)

| File | Byte | SHA-256 |
|---|---:|---|
| `e2e/run-20261001-181644/summary.json` | 2.197 | `8bac356bc54c0a0b…f02a2077` |
| `e2e/run-20261001-181644/chart_canh_bao_phan_bo.png` | 51.103 | `859ac39e02fa9d09…18847ad4` |
| `e2e/run-20261001-181644/chart_chon_phan_bo.png` | 53.251 | `b6787bbc13f453ce…fc94a43e` |
| `e2e/run-20261001-181644/chart_xu_huong.png` | 73.372 | `a03c2479ba2b72f3…08ca2c6b` |
| `e2e/run-20261001-181644/chart_so_sanh_mau.png` | 71.083 | `a9c0ef1addf421f6…235562a5` |
| `e2e/run-20261001-181644/mail_canh_bao.eml` | 71.516 | `edf58042c454c333…87677659` |
| `gates_j1.log` / `j1_ticket_repo.log` / `j1_ticket_mirror.log` / `j1_related149.log` | — | `aeb12497…` / `02165700…` / `7c87414f…` / `9cfc934f…` |

(Danh sách SHA đầy đủ ở `summary.json` + log tương ứng; file CSV trong run dir là bản copy đúng size + SHA-256 `6ebf2930…441c` khớp manifest LSU-1. Danh sách node lỗi: `j1_nodes_only.txt`, đối chiếu nền: `only_b5.txt` — 9 mục bge, `only_j1.txt` — rỗng.)
