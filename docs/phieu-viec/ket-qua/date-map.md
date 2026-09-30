# Vé `date-map` — Map ngày phát sinh thật (`occurred_at`) cho xu hướng/tái phát: nghiệm thu

- Trạng thái: **hoàn tất phần thực thi, chờ Muse review**.
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (repo `.venv`, chạy qua `uv run --no-sync --group dev`; `PYTHONPATH=src;C:/tmp/e3-py311` để có `xlrd`).
- Nhánh: `phieu-viec/rag-fix1`. Commit code: `fa58d26` (cột `occurred_at` toàn tuyến + test) → `b86dab0` (sửa hiệu năng N+1 của hàm fill); các mốc tiến độ chỉ sửa `trang-thai.md`; commit báo cáo ở đỉnh nhánh. Không merge `main`, không force-push.
- Phạm vi ghi: DB copy + artifact trên ổ C (`C:/tmp/date-map/`); repo chỉ nhận code/test + báo cáo + `PROJECT_HANDOVER.md` + `trang-thai.md`. Không ghi index production RAG, không đụng ổ D (dữ liệu).

## 1. Việc 1 — Khảo sát cột ngày trong `Loi KDTPS.xlsx` (dữ liệu thật)

Nguồn: `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/Loi KDTPS.xlsx`
(10.006.929 B, SHA-256 `ee97eaf507dc8c11b8a3fee78ecb944d50019ad7f8c1c8e09cba622e3c461624`),
sheet `History KDTPS`, header dòng 4, **15.737 dòng dữ liệu**. Script khảo sát chỉ-đọc: `C:/tmp/date-map/survey_xy.py`, `survey_all.py` (kết quả `survey_xy.json`, `survey_all.json`).

### 1.1 Sự thật về cột X/Y (ghi chú `buoc0-deploy` nói tới)

| Cột | Header thật | Kiểu dữ liệu | Độ phủ thật |
|---|---|---|---|
| X | `HOLD日 / Ngày Hold` | chuỗi viết tay | 15.727 ô khác rỗng nhưng **15.397 (97,9%) là gạch `ー`**; chỉ **330 ô có ngày thật** (nhiều định dạng: `6/1/2023`, `2/15日`, `2023/4/07`, `ー2024/01/30`…) + 1 ô datetime |
| Y | `HOLD解除日 / Ngày giải Hold` | chuỗi viết tay | tương tự: **237 ô có ngày thật**, còn lại `ー` |

→ X/Y **không phải ngày phát sinh** mà là ngày hold/giải hold; phần "trống" là **thiếu thật trong nguồn** (nguồn dùng `ー` = không áp dụng), không phải lỗi nhập. Không dùng X/Y làm mốc xu hướng.

### 1.2 Cột ngày phát sinh thật: C `生産日 / Ngày tháng sản xuất`

- **15.737/15.737 = 100% là datetime** (không ô trống, không chuỗi lẫn).
- Năm của C khớp **tuyệt đối** năm cột A (2023: 3.420; 2024: 3.876; 2025: 4.857; 2026: 3.584 — 0 dòng lệch).

→ Chọn **cột C** làm nguồn `occurred_at` (ngày phát sinh thật). X/Y chỉ giữ trong `raw_json` như cũ.

## 2. Việc 2 — Mở rộng importer (code + test)

### 2.1 Code (commit `fa58d26`)

- **`schema.sql`**: thêm cột `occurred_at TEXT` (nullable, ISO `YYYY-MM-DD`) — mốc phát sinh thật; `created_at` (lúc nhập) giữ nguyên nghĩa.
- **`store.py`**: `init_db` thêm migration **idempotent** (`ALTER TABLE … ADD COLUMN occurred_at` khi DB cũ thiếu cột); `upsert_case` ghi `occurred_at`.
- **`column_map.py`**: `parse_date_cell()` — nhận `datetime`/`date`, ISO, `YYYY/M/D`, `YYYY.M.D`, `YYYY年M月D日` (hậu tố `日` tuỳ chọn); placeholder `ー`/`-`/`/` và chuỗi lạ → `None` (**không đoán ngày**); `HISTORY_29_DATE_INDEX = 2`; `normalize_history_row` trả thêm `occurred_at`.
- **`import_history.py`**:
  - Đếm `rows_with_occurred_at` trong kết quả import.
  - `fill_occurred_at(conn, xlsx, batch_id=None, apply=False)` cho DB đã nhập trước khi có cột: quét file **chỉ-đọc**, khớp `(batch_id, source_row)` + **đối chiếu lại khoá dedup** `(no_dvd, machine_type, line)` (lệch → `mismatch`, không đụng); chỉ ghi `occurred_at` + `updated_at`; **không đụng `raw_json`** (lý do: force re-import sẽ xoá provenance `_backfill` của vé f3b); dry-run mặc định, `apply=True` mới ghi; idempotent.
  - CLI: `python -m aios_habit.error_cases.import_history --db <db> --xlsx <file> [--apply]`.
- **`trend_analysis.fetch_records`**: `occurred_at` thật, **fallback `created_at`** khi thiếu; `since`/`until` và thứ tự lọc theo cùng mốc.
- **`auto_classifier.detect_recurrence`**: cửa sổ tái phát theo **ngày phát sinh thật** (nguồn ngày-granular → cửa sổ mở rộng theo ngày lịch; dòng không có ngày vẫn dùng `created_at` chính xác tới giây); thêm chặn trên `<= now`.
- Đăng ký: `parse_date_cell`, `HISTORY_29_DATE_INDEX`, `fill_occurred_at` trong `error_cases/__init__.py`.
- **`b86dab0`**: nạp trước 1 lượt các dòng của batch thành dict (bỏ N+1 SELECT/dòng) — 452s → ~5s trên 15.737 dòng.

### 2.2 Test

- **9 bài mới**: `test_error_cases_f2.py` 6 bài (định dạng `parse_date_cell` + placeholder, trích C khi import, C thiếu → NULL, plan/apply/idempotent, không đụng dòng `mismatch`, file lạ → `no_batch`); `test_trend_analysis.py` 2 bài (ưu tiên `occurred_at` khi bucketize + since/until lọc theo ngày phát sinh/fallback); `test_auto_classifier.py` 1 bài (cửa sổ tái phát: `occurred_at` thắng `created_at`, fallback đúng).
- Bộ `error_cases` đầy đủ (10 tệp: f1–f4, lsu_logs, backfill_fix, feedback_loop, investigation_tree, trend, auto_classifier; không tính `test_chat_action_error_lookup` thuộc lane B1-FEAT VM): **127/127 đạt** trên Windows Python 3.11 (nền 118 → +9 bài mới; bài smoke đọc file thật chạy cùng `AIOS_DATA_DIR`).

### 2.3 Trình tự chạy trên dữ liệu thật (DB copy ổ C, có backup)

| Bước | Việc | Kết quả |
|---|---|---|
| 1 | Copy DB f3b `C:/tmp/f3b-backfill/error_cases_f3b.db` (gốc buoc0-deploy `fa9efeba…46d8`) → `C:/tmp/date-map/error_cases_date.db` + backup `error_cases_date.db.bak-20261001-preapply` | SHA-256 cả hai **`44079ad542bc1d7b54e7979360d6b9cb34b520aff9f94195c2d2df21ef556bf7`** (giống bản gốc); `integrity_check=ok` (15.707 ca) |
| 2 | Fresh-import proof: DB mới `fresh_import.db` + importer mới + file thật | 15.737 dòng → **15.724 nhập / 13 bỏ** (thiếu năm/NO hoặc máy/line); `rows_with_occurred_at=15.724`; DB **15.707 ca, occurred_at 15.707/15.707 = 100%**, dải `2023-01-05 … 2026-08-27` |
| 3 | Dry-run `fill_occurred_at` trên bản copy | `would_update=15.707`, `no_change=0`, `invalid_date=0`, `mismatch=0`, `not_in_db=17` (dòng trùng khoá `(no_dvd, machine_type, line)` đã gộp từ lúc import) — **chưa ghi gì** |
| 4 | Apply | **`updated=15.707`** (chỉ `occurred_at` + `updated_at`); `integrity_check=ok` sau apply |
| 5 | Verify độc lập | phủ **100%**; theo năm 3.409 / 3.859 / 4.856 / 3.583; **25/25 mẫu ngẫu nhiên đối chiếu ngược file Excel khớp**; `created_at` **không đổi** (min/max y backup `2026-09-29 19:43:56..19:45:39`); `raw_json._backfill.fix` **còn nguyên 5.461 giá trị** (provenance f3b); `updated_at=2026-09-30 22:26 UTC` |
| 6 | Chạy lại apply (idempotent) | `no_change=15.707`, `updated=0` |

Bằng chứng JSON: `C:/tmp/date-map/out/fill_dryrun.json`, `fill_apply.json`, `verify_apply.json`.

## 3. Việc 3 — Chạy lại Bước 4 (xu hướng) + Bước 5 (tái phát): so sánh trước/sau

Script: `C:/tmp/date-map/compare_trend_recur.py` (chỉ-đọc `mode=ro`), kết quả `out/compare.json`, báo cáo markdown `out/buoc4_truoc.md` / `out/buoc4_sau.md`.
“Trước” = bản DB đã migrate cột nhưng `occurred_at` còn NULL (`error_cases_before_fill.db`, SHA `83c34fbc…`) — đúng hành vi cũ (dùng `created_at` = lúc nhập).

### 3.1 Xu hướng (chu kỳ tuần, ngưỡng 0,2)

| Chiều | Trước | Sau (ngày phát sinh thật) |
|---|---|---|
| Model | **1 bucket** `2026-W40` — 141 dòng bảng, 0 cảnh báo | **174 bucket** `2023-W01 → 2026-W35` — 2.468 dòng, **205 cảnh báo** |
| Line | **1 bucket** — 174 dòng, 0 cảnh báo | **174 bucket** — 2.909 dòng, **66 cảnh báo** |
| Công đoạn | **1 bucket** — 1 dòng, 1 cảnh báo | **174 bucket** — 174 dòng, 174 cảnh báo |

Không còn gom 1 bucket; trục thời gian chạy đúng 3,5 năm dữ liệu thật. (Chiều “Công đoạn” vẫn nhóm `(không rõ)` vì cột F `生産工程` chưa được map — ngoài phạm vi vé; 174 cảnh báo ở đây là do tỉ lệ 100% > ngưỡng với nhóm duy nhất, không liên quan ngày.)

### 3.2 Tái phát (Bước 5)

- **Trước (đo gốc buoc0-deploy, chạy ngay sau nhập)**: `Tái phát: mã ERROR đã phát sinh 3.569 lần trong 12 giờ qua` — mọi bản ghi cùng `created_at` lúc nhập nên "12 giờ qua" vô nghĩa.
- **Sau — mốc thời gian thật**: ref = thời điểm hiện tại → **không còn ca phát sinh trong 12h qua** (dữ liệu thật kết thúc `2026-08-27`) → không báo động giả; ref = ngày phát sinh thật nhiều nhất của mã `ERROR` (**2026-08-21, 15 ca cùng ngày**) → **`Tái phát: mã ERROR đã phát sinh 16 lần trong 12 giờ qua`** (15 ca thật cùng ngày + ca mới) kèm đối sách lấy từ lịch sử — cảnh báo giờ mới có nghĩa vận hành.

### 3.3 Đối chiếu tiêu chí ĐẠT của vé

| Tiêu chí | Kết quả |
|---|---|
| ≥95% bản ghi có `occurred_at` hợp lệ HOẶC chứng minh thiếu thật | **100% (15.707/15.707)** trên DB copy; import mới cũng 100%. Phần X/Y trống là **thiếu thật** trong nguồn (97,9%/98,5% ô chỉ có `ー`) — mục 1.1 |
| Xu hướng theo ngày phát sinh render đúng, không gom 1 bucket | **1 bucket → 174 bucket** (`2023-W01 … 2026-W35`); Bước 5 tính theo ngày thật (16 lần quanh 2026-08-21) |

## 4. Cổng kiểm + ràng buộc

- `compileall` OK; `check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `cli audit` → `"status": "PASS"` (errors/warnings rỗng); `import aios_habit.workspace_chat_app` OK.
- Full suite `pytest -q` (kèm `PYTHONPATH` xlrd + `AIOS_DATA_DIR=C:/tmp/aios-v14-data`): xem mục 4.1 bên dưới (log `C:/tmp/date-map/full_suite_after.txt`).
- Ràng buộc vé: làm trên DB copy ổ C + backup + `integrity_check` trước/sau; không ghi index production; không đụng ổ D (dữ liệu); không merge `main`; không force-push.

### 4.1 Full suite

- `pytest -q` (kèm `PYTHONPATH` xlrd + `AIOS_DATA_DIR=C:/tmp/aios-v14-data`): **3.415 đạt, 2 bỏ qua, 36 lỗi, 4 error** (235,5s) — so nền `f3b-backfill` `3.406/2/36/4`: **+9 đạt, đúng bằng 9 test mới của vé** (không bài cũ nào đổi trạng thái).
- Đối chiếu danh sách bài lỗi/error **theo ID** với nền (`C:/tmp/date-map/baseline_failures.txt` ↔ `after_failures.txt`, diff `comm`): **trùng khít từng bài** — 9 `test_graphify_adapter`, 9 BGE subprocess (6 worker + 3 client), 5 `test_chat_action_error_lookup` (hardcode đường dẫn VM `/home/hatch/...` — lane B1-FEAT, có sẵn ở nền), 4 đóng gói `test_commit_d_wheel_and_packaging`, 4 nhóm `rag_v2` (eval harness 2 + synthesis 1 + dev cli 1), 9 bài lẻ (workspace-chat ×2, owner-pilot, notebook, mom, expert-knowledge, commit-b, chunk-eval, antigravity). **Không bài nào thuộc vé `date-map`.**

## 5. Hạn chế / đề xuất

- Chiều “Công đoạn” trong history_29 chưa có nguồn được map (cột F `生産工程`) → vẫn `(không rõ)`; nếu muốn dùng chiều này cần vé riêng.
- `occurred_at` là **ngày** (nguồn chỉ có ngày); cửa sổ tái phát 12h cho dòng có ngày thật mở rộng theo ngày lịch — đã ghi rõ trong docstring `detect_recurrence`.
- Dữ liệu thật kết thúc `2026-08-27` → cảnh báo “gần đây” sẽ rỗng cho tới khi file nguồn được cập nhật thêm (đúng thực tế, không phải lỗi).
- Muốn phân tích hold thật theo X/Y thì hiện **không đủ dữ liệu** (97,9%/98,5% trống thật); nếu nhà máy bắt đầu duy trì 2 cột này, chỉ cần thêm map tương tự (hạ tầng `fill_*` đã có sẵn mẫu).
