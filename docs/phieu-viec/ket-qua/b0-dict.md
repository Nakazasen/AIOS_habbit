# Vé `B0-DICT` — Từ điển thuật ngữ + số hóa bảng mã lỗi: nghiệm thu trên máy nhà

- Trạng thái: **hoàn tất phần xác minh của OMP trên máy nhà, chờ Muse review**.
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (repo `.venv`, chạy qua `uv run --no-sync --group dev`; kèm `PYTHONPATH=src;C:/tmp/e3-py311` — có `xlrd`/`openpyxl`, cùng cách các vé trước).
- Nhánh: `phieu-viec/rag-fix1`. Code của vé (Muse, lane [VM]): commit `1818297` + `a3ec49a` (head `a3ec49a`), 13 tệp: `error_cases/glossary.py` (+462), `glossary_schema.sql` (+18), `import_history.py` (+55), `column_map.py`, `store.py`, `auto_classifier.py`, `case_form.py`, `chat_action_error_lookup.py`, `__init__.py`, `schema.sql`, `tests/test_b0_dict.py` (+497), fix hermetic `tests/test_b0_form.py`. OMP **chỉ verify, không sửa code**.
- Nhận vé bước verify qua watcher (nó tự mở OMP LAUNCH 1/4 lúc 09:08:24); **cổng gate ĐẠT** khi điều kiện mở tới (Muse báo code+test xong 09:13–09:15) — không dùng nhánh "4 lần watcher"/`cho-muse` (ghi mốc tại commit `13bc6cf`, số liệu tại `c1ee4bf`).
- Phạm vi ghi: bản copy DB + artifact trên ổ C (`C:/tmp/b0-dict/`); repo chỉ nhận `trang-thai.md` + báo cáo này. Không ghi index production RAG, không đụng ổ D (dữ liệu), không merge `main`, không force-push.

## 1. Việc 1 — Bộ test của vé trên máy nhà

- `pytest tests/test_b0_dict.py -q` (kèm `AIOS_DATA_DIR=C:/tmp/aios-v14-data`): **24/24 đạt** trên Windows/Python 3.11.14 (Muse đã chạy 24/24 trên VM Linux 3.12.3) — 9,17 giây.
- Bộ test chạy trên **file nguồn thật** (đọc-only) trong `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/`, không dùng fixture giả.

## 2. Việc 2 — Đo tiêu chí + smoke trên DB THẬT (bản copy, có backup)

### 2.1 Nguồn + an toàn dữ liệu

| Việc | Kết quả |
|---|---|
| Nguồn | `C:/tmp/date-map/error_cases_date.db` — DB thật 15.707 ca (đã `occurred_at` + f3b-backfill), **53.268.480 B** |
| SHA-256 nguồn | `a362e571977cae31da24aafa14d97a3dbf603eee8430ada134253b31d2a64cf0` (trùng số đo vé B0-FORM) |
| Copy làm việc | `C:/tmp/b0-dict/error_cases_dict.db` — **byte-identical** (SHA khớp trước khi ghi) |
| `integrity_check` trước / sau | `ok` / `ok` |
| SHA-256 sau các bước ghi | `3dad67fe5fa94b3c723cf3e4a4b45ea933ed59dc2d8deeb869d734c6f29e3d97` |
| DB gốc | không mở ở chế độ ghi (chỉ copy + đọc) |

Script: `C:/tmp/b0-dict/verify_b0_dict.py` + `verify_b0_dict_extra.py`; kết quả JSON: `C:/tmp/b0-dict/verify_result.json`, `verify_extra.json`.

### 2.2 Migrate + `backfill_error_code_i` (cột mã thật trích từ cột I của lịch sử)

| Bước | Kết quả |
|---|---|
| Cột `error_code_i` trước migrate | **chưa có** (DB deploy cũ) → `init_db` thêm idempotent |
| Dry-run | đọc 15.707 dòng → **trích được 3.056** / 12.651 dòng không có mã trong text |
| Apply | **updated 3.056**; chạy lại lần 2: **0 đổi** (`no_change=3.056`) — idempotent |
| Mẫu thật | `2023/2 → F000`, `2023/5 → JAM9600`, `2023/16 → C2340`, `2023/48 → F010`, `2023/78 → JAM4212`, `2023/91 → C6900`, … |

### 2.3 Import từ điển từ 6 file nguồn thật

| Nguồn (trong `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/`) | Kết quả |
|---|---|
| `02XC_自己診断表示一覧表-Iris2020 VN.xls` (C_CALL, 4 bảng F4) | `skipped` — file chưa đổi, dữ liệu đã có từ `buoc0-deploy` |
| `Iris2020_Cコール自己診断.xlsx` (sổ chẩn đoán 2025, mới) | `imported`: làm giàu **179** mục + thêm **11 mã** (225 mục) |
| `02XC_自己診断表示一覧表.xls` (bảng cũ 2024) | `imported`: thêm **8 mã** (236 mục) — phần còn lại của 10 mã C cũ |
| `UWCAシステムエラー(FXXX)概要.xls` (F_SYSTEM) | `skipped` — chưa đổi |
| `SCT自動調整エラーコード一覧_140221.xls` (SCT_ADJ) | `skipped` — chưa đổi |
| `02XC_機能定義書_JAM一覧 (1).xls` (JAM) | `skipped` — chưa đổi |

- Từ điển: **3.820 → 3.839 mục** (C_CALL 226→245, F_SYSTEM 127, JAM 3.430, SCT_ADJ 37); alias `term_aliases` = **960**, chạy lại seed = 0 (idempotent); `glossary_imports` giữ đủ 6 dòng provenance.
- **10 mã C cũ 2024 bị bảng VN mới bỏ — tất cả tra được** (đúng điều vé yêu cầu):
  - `C1420`, `C1760` → nguồn `Iris2020_Cコール自己診断.xlsx` (sổ 2025, có cả tên VI + quy trình);
  - `C7631/C7632/C7633/C7634`, `C7641/C7642/C7643/C7644` → nguồn `02XC_自己診断表示一覧表.xls` (bảng cũ 2024, tên JP nguyên văn).
  - Chạy lại 2 importer: `skipped` (không nhân bản dữ liệu).

### 2.4 Tiêu chí nghiệm thu — % mã lỗi trong DB tra được trong từ điển

- **272 mã phân biệt** trong DB thật (từ `error_code_c/h/i`) — **185 tra được = `68,01%`**.
- **Khớp số Muse đo trên VM (185/272 = 68,01%)**; trước fix Muse đo 46,69% (OMP không đo lại bản cũ).
- Còn **87 mã chưa có (41 mã C + 46 mã F)** → danh sách đầy đủ: `C:/tmp/b0-dict/unmatched_codes.json` (đầu vào vé B0-MEASURE).
- Phân bố tra được theo họ: C_CALL 126 · JAM 58 · F_SYSTEM 1.

### 2.5 Smoke 3 nơi dùng từ điển (đúng đường code sản phẩm)

| Nơi | Kết quả thực tế |
|---|---|
| **Tra cứu Bước 1** (chat action `tra_cuu_loi_tuong_tu`) | `C0030` → `_Từ điển mã lỗi (C_CALL): Bất thường hệ thống bản mạch FAX_ — … · **Nguồn: 02XC_自己診断表示一覧表-Iris2020 VN.xls**`; `F000` → tra được (F_SYSTEM, UWCA); `F010` → **không có card từ điển** (chưa có trong từ điển) |
| **Form B0-FORM** | nhập `F010` → validate cảnh báo `"Mã lỗi 'F010' lạ — chưa có trong từ điển. Vẫn ghi nhận…"`, 0 lỗi chặn; ca âm `Z9999` + ngày hợp lệ → **ghi được** `FORM-20261001-0001` kèm cảnh báo (đúng thiết kế "chỉ cảnh báo") |
| **Chống trùng form ↔ lịch sử (fix bonus b)** | ca thật `2023/1203` (`C4701` chỉ nằm ở cột I) tra bằng mã thật → **"Trùng ca đã có … mã phiếu 2023/1203. Không nhập đúp."** — dedup qua `error_code_i` chạy đúng trên DB thật |
| **Phân loại Bước 5** | `classify_error("FAX基板システム異常")` → họ `C_CALL`, lý do `"Chuẩn hóa tên gọi: 'FAX基板システム異常' -> C_CALL C0030"` + `Tra cứu glossary: … có trong từ điển` |
| **Gợi ý nhập form** | `suggest_terms("FAX")` → C0950/C0920/C0830 kèm nghĩa + nguồn (API từ điển + test; xem đề nghị mục 4) |
| **Chuẩn hóa tên gọi** | `canonical_term("JAM4709")` → `(JAM, 4709)`; tên biến thể JP → `(C_CALL, C0030)`; chuỗi lạ → `None` |
| **Bẫy chữ F tiếng Anh** | `extract_code_from_text("FEED kẹt giấy") = None`; `"máy báo C4701…" = "C4701"` |

## 3. Việc 3 — Cổng kiểm

- `compileall src tests` → PASS; `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `cli audit` → `{"status": "PASS"}`; `import aios_habit.workspace_chat_app` → OK; `git diff --check` sạch; `git status` sạch (trước khi commit báo cáo).
- Full suite `pytest -q --tb=no -rfE` (kèm `PYTHONPATH` xlrd + `AIOS_DATA_DIR=C:/tmp/aios-v14-data`): **3.474 đạt / 2 bỏ qua / 35 lỗi / 4 error** (558,3 s). So nền `B0-FORM` (3.449/2/36/4): **+25 đạt** = 24 bài mới của vé + 1 bài đỏ cũ chuyển xanh; **−1 lỗi** (đúng bài cũ đó); 4 error giữ nguyên (nhóm `test_chat_action_error_lookup` cần dữ liệu VM — có sẵn, không liên quan vé).
- Đối chiếu danh sách bài lỗi/error **theo ID** với nền `B0-FORM` (script `C:/tmp/b0-dict/compare_failures.py`, nguồn cache `.pytest_cache/lastfailed` + log nền): khác biệt đúng **−1** — `tests/test_b0_form.py::test_action_no_db_returns_none_and_creates_nothing` (bài đỏ va chạm môi trường trước đây **nay xanh** nhờ fix hermetic của vé). **Không bài nền nào thoái lui.** Ba mục "+" còn thấy trong cache đều là **rác từ lượt chạy cũ, không thuộc lượt này và không còn tồn tại trong repo** (2 đường dẫn `tests/fixtures/agent_harness/code_workspace/…` không có trên đĩa; 1 ID test đã bị đổi tên trong `test_agent_error_report_artifact.py`) — đã kiểm bằng `--collect-only`/rerun, không có dòng tương ứng trong summary `-rfE` của lượt chạy.

## 4. Kết luận / đề nghị

- Tiêu chí vé dành cho OMP **đạt trên máy nhà với DB thật**: (1) con số % = **68,01%** (185/272, khớp Muse); (2) tra mã có → **nghĩa + nguồn**; mã chưa có → **"chưa có trong từ điển"** (form cảnh báo, chat không có card); (3) 3 lỗi dữ liệu thật (10 mã C cũ, JAM strip prefix, bẫy chữ FEED/FACE) đều xác nhận có test + xác nhận lại trên dữ liệu thật.
- Đề nghị Muse (OMP không tự sửa — lane [VM]):
  - (a) `suggest_terms()` hiện là API + test của từ điển, **chưa render trực tiếp trong template form**; nếu muốn "gợi ý khi nhập form" ở mức UI thì cần một nhát nối nhỏ trong `chat_action_case_form` (hoặc xác nhận mức API là đủ cho vé);
  - (b) cân nhắc bổ sung mục B0-DICT vào tài liệu canonical (`ARCHITECTURE.md` / `PROJECT_HANDOVER.md`) khi trả verdict, như đã làm cho B0-FORM;
  - (c) danh sách 87 mã chưa có (`C:/tmp/b0-dict/unmatched_codes.json`) dùng làm đầu vào B0-MEASURE.
- Ràng buộc giữ: chỉ ghi bản copy ổ C (backup + `integrity_check` trước/sau); không ghi index production; không đụng ổ D (dữ liệu); không merge `main`; không force-push.
