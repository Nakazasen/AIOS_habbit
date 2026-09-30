# Vé `f3b-backfill` — Backfill trường `fix` (gate F3b đang mở): nghiệm thu

- Trạng thái: **hoàn tất phần thực thi, chờ Muse review**.
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (repo `.venv`, chạy qua `uv run --no-sync --group dev`; `PYTHONPATH=src;C:/tmp/e3-py311` để có `xlrd`).
- Nhánh: `phieu-viec/rag-fix1`. Commit code: `9b4baef` (module + test) → `3919aba` (bổ sung biến thể marker `lập biểu/viết biểu`); các mốc tiến độ chỉ sửa `trang-thai.md`; commit báo cáo ở đỉnh nhánh. Không merge `main`, không force-push.
- Phạm vi ghi: DB copy + artifact trên ổ C (`C:/tmp/f3b-backfill/`); repo chỉ nhận code/test + báo cáo + `trang-thai.md`. Không ghi index production RAG, không đụng ổ D (dữ liệu).

## 1. Việc 1 — Phân tích 43,3% ca thiếu `fix` (dữ liệu thật)

Nguồn: DB `error_cases` của vé `buoc0-deploy` — `C:/tmp/buoc0-deploy/error_cases_deploy.db`
(49.881.088 B, SHA-256 `fa9efeba5693df18e49341067cce49293895f00dc71c5d2dc7b7222c294946d8`),
15.707 ca `history_29` nhập từ `Loi KDTPS.xlsx`, sheet “History KDTPS”.

### 1.1 Phân bố thiếu `fix` (cột AB “改造 / Kaizo”)

| Nhóm | Số ca | Ghi chú |
|---|---:|---|
| `fix` đã đầy (AB có giá trị) | 8.912 (56,74%) | 2023–2024 dùng `不要` (7.180), `要` (83), `Link(jp+vn)` (1.083), `ー` (566) |
| `fix` trống (AB rỗng) | **6.795 (43,26%)** | tập trung 2025–2026 |

| Năm | Số ca | AB trống | % trống |
|---|---:|---:|---:|
| 2023 | 3.409 | 4 | 0,1% |
| 2024 | 3.859 | 1 | 0,0% |
| 2025 | 4.856 | 4.208 | 86,7% |
| 2026 | 3.583 | 2.582 | 72,1% |

**Nguyên nhân thiếu**: từ 2025 cột AB gần như không còn được duy trì (chỉ ghi `Link(jp+vn)` khi có báo cáo cải tiến, `ー` khi không có); 2023–2024 ghi `不要/要` gần đủ.

### 1.2 Có trích được từ cột khác không?

- Không có cột “đối sách” riêng; cột `AC` (link báo cáo) **rỗng ở toàn bộ 6.795 ca trống** (kể cả các ca `Link`).
- Nhưng **N/O (調査状況 / Tình trạng điều tra) đầy 99,5–100%** và **chứa câu đối sách/kết luận xử lý ghi nguyên văn**: `Đối ứng…`, `Đối sách…`, `Xử lý…`, `Thay thế…`, `Upsoft lại…`, `lọc hàng…`, `Lập biểu không tái hiện…`, `cho máy đi/quay lại line`, `対策：…`, `処置…`, `交換…`, `再現せず不良に処理`…
- Đo trên dữ liệu thật: **5.461/6.795 ca trống (80,4%) trích được câu xử lý nguyên văn**; 1.334 ca còn lại không có câu đối sách/kết luận (mục 7).
- Kết luận Việc 1: phần thiếu **không phải thiếu thật toàn bộ** — 80,4% nằm ở cột N/O dưới dạng văn bản; 19,6% còn lại là ca chưa có kết luận (đa số đang điều tra).

## 2. Việc 2 — Script backfill (code + test; dry-run trước; backup trước apply)

### 2.1 Code

- **Mới** `src/aios_habit/error_cases/backfill_fix.py` (commit `9b4baef`):
  - Trích **nguyên văn** đoạn xử lý: từ **dòng khớp marker cuối cùng** trong ô nguồn đến hết ô (strip), không cắt/không viết lại chữ nào.
  - Nguồn: **O (VN) ưu tiên, fallback N (JP)** — cùng quy ước với `investigation`.
  - 29 marker VN (khớp không phân biệt hoa/thường): `đối ứng, đối sách, khắc phục, biện pháp, phương án, xử lý, thay thế, thay mới, sửa chữa, vệ sinh, làm sạch, lọc hàng, thu hồi, upsoft, up soft, nạp lại, cài lại, đào tạo lại, hướng dẫn lại, nhắc nhở, cải tiến, triển khai, chú ý, bổ sung, cho máy, làm biểu, lập biểu, viết biểu, đơn phát`.
  - 17 marker JP (phân biệt hoa/thường vô nghĩa): `対策, 是正, 改善, 改造, 処置, 処理, 交換, 修理, 清掃, 再結線, 水平展開, 再発防止, 復帰, 対応, 注意, 教育, 指導`.
  - **Không** dùng các từ chỉ-điều-tra (`kiểm tra`, `làm lại`, `thực hiện lại`, `やり直し`, `確認`) và **không** dùng `thay` trần (trùng `thay vì/thay đổi`).
  - `plan` = dry-run (chỉ đọc) → `apply` ghi **provenance từng giá trị** vào `raw_json["_backfill"]["fix"]`:
    `value` (nguyên văn), `source` (`O`/`N`), `marker`, `rule` (`f3b-fix-v1`), `line` (dòng 1-based trong ô), `chars`, `at` (giờ máy).
  - An toàn: chỉ ghi `raw_json`; bỏ qua ca AB đã đầy hoặc đã có backfill (idempotent; `--refresh` mới ghi lại); không đổi schema.
  - CLI: `python -m aios_habit.error_cases.backfill_fix --db <db> [--apply] [--samples N] [--json-out F]` (mặc định dry-run).
- **Sửa** `src/aios_habit/error_cases/completeness.py`: `fix` trống AB nhưng có giá trị backfill → tính `filled`; thêm bộ đếm `backfilled` theo từng trường; công khai `detect_format/is_filled/backfill_value` để tái dùng. Gate vẫn tính trên tập áp dụng (`history_29`), không đổi ngưỡng 90%.
- Đăng ký API: `plan_fix_backfill`, `apply_fix_backfill`, `extract_fix_segment`, `FIX_MARKERS_VN/JP`, `FIX_BACKFILL_RULE` trong `error_cases/__init__.py`.

### 2.2 Test

- Mới `tests/test_error_cases_backfill_fix.py` — **16 bài** (15 bài trong commit `9b4baef` + 1 bài biến thể marker trong commit `3919aba`): trích nguyên văn (marker cuối → hết ô), ưu tiên O, không marker → `None`, khớp hoa/thường, biến thể `lập biểu/viết biểu`; plan đếm đúng + không ghi; apply ghi provenance đúng cấu trúc, idempotent, `refresh`, bỏ qua AB đã đầy; tích hợp gate (`filled/backfilled`, giá trị rỗng không tính).
- Bộ `error_cases` đầy đủ (11 tệp): **121/121 đạt** trên Windows Python 3.11 (nền trước vé 105/105; +16 test mới của vé).

### 2.3 Trình tự chạy trên dữ liệu thật (DB copy ổ C, có backup)

| Bước | Việc | Kết quả |
|---|---|---|
| 1 | Copy DB gốc ra `C:/tmp/f3b-backfill/error_cases_f3b.db` | SHA trùng bản gốc `fa9efeba…46d8` |
| 2 | `PRAGMA integrity_check` + `quick_check` trước apply | `ok` / `ok` |
| 3 | **Dry-run** (`--json-out dryrun_final.json`) | 15.707 ca quét; AB trống 6.795; **trích được 5.461** (O 5.049 / N 412); không trích 1.334; không ghi gì |
| 4 | **Backup** `error_cases_f3b.db.bak-20261001-preapply` + băm lại | SHA `fa9efeba…46d8` (= bản gốc) |
| 5 | **Apply** (`--apply --json-out apply_final.json`) | **ghi 5.461 ca** (bỏ qua AB-đầy 0, đã-có 0); lúc `2026-10-01T04:35:24+07:00` |
| 6 | `integrity_check` + `quick_check` sau apply | `ok` / `ok` |

Artifact + SHA-256:

| File | Size (B) | SHA-256 |
|---|---:|---|
| DB gốc buoc0-deploy (nguồn) | 49.881.088 | `fa9efeba5693df18e49341067cce49293895f00dc71c5d2dc7b7222c294946d8` |
| Backup trước apply | 49.881.088 | `fa9efeba5693df18e49341067cce49293895f00dc71c5d2dc7b7222c294946d8` |
| `dryrun_final.json` (kế hoạch đầy đủ) | 1.978.516 | `d46d81168746a3f7a8fc0b096acac50af3284e559aa72471e00b2101c0efda4e` |
| `apply_final.json` (kết quả ghi) | 1.978.636 | `5e04e0c321380d7be8d9ff174af264f70d542c937497348b471c9d0f0cb4b81a` |
| DB sau apply | 52.916.224 | `44079ad542bc1d7b54e7979360d6b9cb34b520aff9f94195c2d2df21ef556bf7` |

Marker dùng nhiều nhất (44/46 marker được dùng, 5.461 giá trị): `xử lý` (1.328), `cho máy` (799), `đối sách` (399), `thay thế` (327), `chú ý` (308), `lập biểu` (256), `đối ứng` (252), `vệ sinh` (188), `lọc hàng` (173), `交換` (154)…

## 3. Việc 3 — Chạy lại gate F3b trên DB đã backfill

`completeness.measure` (toàn bộ 15.707 ca `history_29`):

| Trường | Trước | Sau | Backfilled |
|---|---:|---:|---:|
| no_dvd | 15.707/15.707 = 100,00% | 100,00% | 0 |
| machine_type | 100,00% | 100,00% | 0 |
| line | 100,00% | 100,00% | 0 |
| department | 99,94% | 99,94% | 0 |
| handler | 0,00% (ngoài lõi, đã biết) | 0,00% | 0 |
| date | 100,00% | 100,00% | 0 |
| investigation | 100,00% | 100,00% | 0 |
| cause | 99,95% | 99,95% | 0 |
| **fix** | **8.912/15.707 = 56,74% → FAIL** | **14.373/15.707 = 91,51% → OK** | 5.461 |
| source_row | 100,00% | 100,00% | 0 |

- Trước: `needs_f3b=True`, `f3b_fields=['fix']`. Sau: **`needs_f3b=False`, `f3b_fields=[]`** → **gate F3b đóng** với dữ liệu đã backfill.
- Cách tính “đầy” sau vé: `fix` = giá trị AB gốc (8.912 ca) **hoặc** giá trị backfill có provenance (5.461 ca). Báo cáo tách riêng `backfilled` để kiểm toán, không trộn.

## 4. Kiểm chứng độc lập (không bịa: đối chiếu ô gốc xlsx)

Đối chiếu từng giá trị với ô nguồn trong `Loi KDTPS.xlsx` (đọc lại bằng openpyxl; kiểm tra `value` == đoạn đuôi nguyên văn của ô tại đúng dòng đã ghi trong provenance):

| Tập mẫu | Kết quả |
|---|---|
| 40 ca ngẫu nhiên (seed 42) toàn bộ nhóm backfill | **40/40 khớp nguyên văn** (0 lệch); AB trong xlsx của các ca mẫu đều trống |
| 40 ca stratified (20 ca nguồn O + 20 ca nguồn N) | **40/40 khớp nguyên văn** |
| 15 ca thuộc nhóm marker mới `lập biểu/viết biểu` | **15/15 khớp nguyên văn** |

Kiểm tra thêm: `AB` gốc **không bị thay đổi** (số ca AB đầy vẫn 8.912); chỉ `raw_json` đổi (thêm khoá `_backfill`), đúng 5.461 ca; `integrity_check`/`quick_check` = `ok` trước và sau apply. Chạy lại dry-run sau apply: 5.461 ca “đã backfill trước”, **0 ca mới**, SHA DB không đổi `44079ad5…6bf7` (idempotent đầu-cuối).

## 5. Cổng nền (trên máy nhà, Windows Python 3.11)

- `uv run --no-sync --group dev python -m compileall src tests` → OK.
- `uv run --no-sync --group dev python scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- Bộ `error_cases` (11 tệp): **121/121 đạt**.
- Full suite `pytest -q` (kèm `PYTHONPATH` xlrd + `AIOS_DATA_DIR=C:/tmp/aios-v14-data`; log đầy đủ `C:/tmp/f3b-backfill/full_suite_after.txt`): **3.406 đạt, 2 bỏ qua, 36 lỗi, 4 error** (166,79s) — so nền LSU-1 `3.389/2/36/4`: **+17 đạt** (16 test mới của vé + 1 test LSU thêm sau lần chạy nền); danh sách 36 lỗi + 4 error **trùng từng bài** với nền (đã diff ID theo log `C:/tmp/lsu1-deploy/full_suite.log`): 9 `graphify_adapter`, 9 BGE worker/client, 4 đóng gói, 4 `rag_v2`, 9 bài lẻ workspace-chat/mom/notebook/owner-pilot/antigravity/chunk-eval/commit-b, 5 bài `test_chat_action_error_lookup` (hardcode đường dẫn VM — lane B1-FEAT) → **không bài nào thuộc vé này**.
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"` (errors/warnings rỗng).
- `python -c "import aios_habit.workspace_chat_app"` → `IMPORT_OK`.
- `git diff --check` sạch; `git status --short` sạch tại commit báo cáo.

## 6. Ràng buộc vé — đều giữ

- **Làm trên DB copy ổ C**: bản gốc `C:/tmp/buoc0-deploy/error_cases_deploy.db` được copy ra `C:/tmp/f3b-backfill/error_cases_f3b.db`; mọi thao tác ghi trên bản copy; có backup + integrity ok trước apply.
- **Không ghi index production RAG**: chỉ mở/ghi file SQLite `error_cases` riêng trên ổ C; không mở index.
- **Không đụng ổ D (dữ liệu)**: DB + output + log trên ổ C; repo chỉ thêm code/test/báo cáo/`trang-thai.md`.
- **Dữ liệu thật không commit**: báo cáo chỉ ghi đường dẫn + số liệu + SHA; không dán nội dung ô dài; artifact đầy đủ nằm trên ổ C (`apply_final.json` chứa cả 5.461 giá trị để Muse kiểm toán).
- **Không merge `main`, không force-push.**

## 7. 1.334 ca còn lại — thiếu thật (không trích được) + đề xuất thu thập

Cấu trúc theo cột `Q` (kì hạn/trạng thái vụ): **đang mở `BTCL/BTCD` 686 ca (51,4%)**, `Close` 387 ca (29,0%), khác 261 ca (19,6%). Nội dung N/O các ca này chỉ có: số đo/kiểm tra hiện trạng, `Liên lạc KTCT điều tra`, `NN: đang điều tra` → **chưa có câu đối sách/kết luận để trích**.

Lưu ý ranh giới kỹ thuật (trung thực): một số ít ca dùng cách diễn đạt không có marker chuẩn (ví dụ `Thay X mới → OK` đứng trần, hoặc `Tăng cường 5S`) nên chưa được trích; nhóm này nhỏ và có thể mở rộng marker ở vé sau nếu user muốn (đổi `rule` mới để phân biệt).

**Đề xuất thu thập bổ sung**: yêu cầu nhà máy điền lại cột `改造` (AB) và `報告書リンク` (AC) cho 2025–2026 theo quy ước cũ (`不要/要/Link`), hoặc bắt buộc ghi kết luận xử lý khi đóng vụ (`Close`) — đây là nguồn chuẩn thay vì suy diễn từ văn bản điều tra.

## 8. Cổng gate watcher

Watcher tự mở OMP **1/4** lúc `2026-10-01T04:14:52` (`launchStallCount=1`); điều kiện mở đã thoả ngay (verdict LSU-1 ĐẠT + dữ liệu thật còn nguyên + Python 3.11 sẵn) → nhận vé, cập nhật mốc tiến độ (04:16 / 04:26 / 04:31 / 04:37) → **không chuyển `cho-muse`, không quay no-op**.

## 9. Kết luận

Vé `f3b-backfill` **hoàn tất phần thực thi**: phân tích chứng minh 80,4% ca thiếu `fix` trích được từ cột điều tra N/O; script backfill (code + 16 test; dry-run + backup + integrity trước apply) đã chạy trên DB copy ổ C, ghi **5.461 giá trị nguyên văn có provenance từng giá trị**; **gate F3b: `fix` 56,74% → 91,51% (≥90%), `needs_f3b=False`**; verify độc lập với ô gốc xlsx 95/95 mẫu khớp nguyên văn; bộ `error_cases` 121/121; ràng buộc vé đều giữ. Chờ Muse review + verdict.
