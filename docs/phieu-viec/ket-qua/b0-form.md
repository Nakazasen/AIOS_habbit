# Vé `B0-FORM` — Form nhập liệu chuẩn Bước 0 (12 trường, ghi thẳng DB): nghiệm thu trên máy nhà

- Trạng thái: **hoàn tất phần xác minh của OMP trên máy nhà, chờ Muse review**.
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (repo `.venv`, chạy qua `uv run --no-sync --group dev`; kèm `PYTHONPATH=src;C:/tmp/e3-py311` để có `xlrd` — tình trạng có sẵn của máy nhà, các vé trước dùng cùng cách).
- Nhánh: `phieu-viec/rag-fix1`. Code của vé (Muse, lane [VM]): commit `cf730d7` — 7 tệp, toàn thêm mới (+1.232 dòng): `error_cases/case_form.py` (+469), `chat_action_case_form.py` (+168), `tests/test_b0_form.py` (+544), `error_cases/schema.sql` (+10), `error_cases/store.py` (+12), `error_cases/__init__.py` (+28), `chat_action.py` (+1 dòng đăng ký `BUILTIN_ACTION_MODULES`). OMP **chỉ verify, không sửa code**.
- Phạm vi ghi: bản copy DB + artifact trên ổ C (`C:/tmp/b0-form/`); repo chỉ nhận `trang-thai.md` + báo cáo này. Không ghi index production RAG, không đụng ổ D (dữ liệu), không merge `main`, không force-push.
- Feature flag: `AIOS_FEATURE_CHAT_ACTION` mặc định **TẮT** (fail-closed, `src/aios_habit/feature_flags.py:36`) — form chỉ hoạt động khi bật cờ, không đổi UI mặc định; `cf730d7` không đụng tệp giao diện nào (chỉ +1 dòng đăng ký action).

## 1. Việc 1 — Bộ test của vé trên máy nhà

- `pytest tests/test_b0_form.py -q`: **33/34 đạt** trên Windows/Python 3.11.14 (Muse đã chạy 34/34 trên VM Linux 3.12.3).
- 1 bài đỏ: `test_action_no_db_returns_none_and_creates_nothing` — **va chạm môi trường máy nhà**, không phải lỗi logic:
  - Bài giả định "máy không có DB nào" (`context` trỏ file thiếu + không env + không DB well-known) → `_handler` phải trả `None`.
  - Trên máy nhà tồn tại thật `C:/tmp/buoc0-deploy/error_cases_deploy.db` (49.881.088 B), nằm trong `_DEFAULT_DB_CANDIDATES` của `chat_action_case_form.py`, nên `resolve_db_path` trả DB đó và handler render **template form** (đúng thiết kế fallback "chạy được ngay trên máy nhà").
  - Phần "creates nothing" của bài vẫn đúng: không file nào được tạo (`missing.exists()` = False); bài chỉ sai ở kỳ vọng `None`.
  - Đề xuất cho Muse (OMP không tự sửa — lane [VM]): làm bài test hermetic bằng `monkeypatch` `chat_action_case_form._DEFAULT_DB_CANDIDATES = ()` (+ bảo đảm `AIOS_ERROR_CASES_DB` không được đặt) để không phụ thuộc việc máy có DB well-known hay không.

## 2. Việc 2 — Nhập thử trên DB thật (bản copy, có backup)

### 2.1 Nguồn + an toàn dữ liệu

| Việc | Kết quả |
|---|---|
| Nguồn | `C:/tmp/date-map/error_cases_date.db` (DB thật đã áp `occurred_at` + f3b-backfill) |
| Copy làm việc | `C:/tmp/b0-form/error_cases_form.db` |
| Backup trước ghi | `C:/tmp/b0-form/error_cases_form.db.bak-20261001-preapply` |
| SHA-256 cả 3 bản (trước) | `a362e571977cae31da24aafa14d97a3dbf603eee8430ada134253b31d2a64cf0` |
| `integrity_check` trước / sau | `ok` / `ok` — 15.707 → **15.711 ca** |
| SHA-256 sau ghi | `2b9385275b5e307190fa4a39fdeee670dbc89c7308cc2a80a15961ab157fd050` |

Đường chạy là **đúng đường chat action** (`_handler` của `chat_action_case_form` — cùng nhánh mà Workspace Chat gọi): hint → template trong vùng trả lời → gửi form `Label: value` bắt đầu bằng `nộp báo cáo` → validate → chống trùng → ghi thẳng DB. Script: `C:/tmp/b0-form/b0_form_smoke.py`; kết quả JSON: `C:/tmp/b0-form/smoke_result.json`.

### 2.2 Ba ca thật đưa vào (giá trị nguyên văn từ DB thật)

Ánh xạ cột nguồn (raw_json của `Loi KDTPS.xlsx`): Model = D, Line = E, Công đoạn = F, Tên lỗi = H, Error code = I, Hiện tượng = L, Nội dung điều tra = O, Nguyên nhân = Z, Đối sách = `_backfill.fix` (trích từ O), Bộ phận PT = P, Ngày phát sinh = `occurred_at`. Giá trị nhiều dòng được nối bằng ` / ` cho hợp định dạng form dòng-based; các giá trị khác giữ nguyên văn.

| Ca | Nguồn (DB id / mã phiếu) | Nội dung chính | Kết quả |
|---|---|---|---|
| A | `15668` / `2026/2396` | `Iris2024 上位` / C33 / 調整A5 / `C CALL` / **C4701** (có trong từ điển) / occ 2026-08-25 | **Đã ghi nhận** `FORM-20261001-0001`, không cảnh báo |
| B | `15689` / `2026/2417` | `6th Next` / C25 / 調整A1.1 / `F CALL` / **F000** / occ 2026-08-26 | **Đã ghi nhận** `FORM-20261001-0002`, không cảnh báo |
| C | `15683` / `2026/2411` | `Iris2024 下位` / C34 / 調整A5 / `JAM` / **JAM4012** / occ 2026-08-25 | **Đã ghi nhận** `FORM-20261001-0003` + ⚠️ cảnh báo mã lạ (chưa có trong từ điển — đúng thiết kế, vé B0-DICT bổ sung sau) |

Ghi chú: 3 ca này chưa từng tồn tại trong DB với mã chính xác (DB lịch sử lưu cột H dạng nhóm — xem 2.4), nên cả 3 **nhập mới sạch**.

### 2.3 Kịch bản kiểm đầy đủ + kết quả

| # | Thao tác | Kết quả thực tế |
|---|---|---|
| 0 | Hint `nhập báo cáo lỗi` trên DB thật | Template form hiện trong vùng trả lời, **đủ 13 nhãn** (12 trường của vé, "Ngày phát sinh"/"Ngày đóng" tách 2 dòng) |
| 1-3 | 3 ca thật A/B/C | 3 dòng mới; **đủ trường trong DB**: model/line/process_stage/error_name/error_code/phenomenon/investigation/cause/countermeasure/department/occurred_at (+ `closed_at`/`report_link` để trống — nguồn thật không có, 2 cột đã tồn tại và ghi được theo test của vé) |
| 4 | Gửi lại y nguyên ca A | **"Không nhập đúp"** — trùng `(model, line, error code, ngày phát sinh)`, chỉ về `FORM-20261001-0001`, không ghi thêm |
| 5 | Ca A thiếu `Đối sách` | **"Chưa ghi được"** — chặn đúng: "Thiếu trường bắt buộc: Đối sách", DB không đổi |
| 6 | Ca A thay mã `C9999` (mã lạ) | **Vẫn ghi nhận** `FORM-20261001-0004` + ⚠️ cảnh báo mã lạ (không chặn) |
| 7 | Ca A `Ngày đóng` (2026-08-20) < `Ngày phát sinh` (2026-08-25) | **"Chưa ghi được"** — chặn đúng thông báo ngày |

- **Không sinh file rời**: `files_new = []` (so danh sách tệp thư mục làm việc trước/sau); form chỉ ghi DB.
- Migration trên DB cũ thật: 7 cột mới (`process_stage, error_name, phenomenon, cause, countermeasure, closed_at, report_link`) được `ensure_form_schema` **tự thêm idempotent** vào DB 15.707 ca (trước ghi chưa có cột nào).
- Provenance: tất cả dòng mới thuộc **batch chia sẻ** `FORM-nhap-lieu` / sheet `form` (id 2, `rows_imported=4`), mã phiếu tự sinh `FORM-YYYYMMDD-NNNN`; `error_code` C-call vào `error_code_c`, còn lại vào `error_code_h` (đúng thiết kế `split_error_code`).

### 2.4 Phát hiện cho Muse — chống trùng với dữ liệu lịch sử

Probe trước khi ghi (trên bản copy sạch): ca thật `15668` tồn tại trong DB, nhưng:

| Cách nhập mã | `find_duplicate_case` | Giải thích |
|---|---|---|
| Mã thật `C4701` (cột I nguồn) | **false — không thấy trùng** | Lịch sử lưu `error_code_h = "C CALL"` (nhóm, cột H); mã thật C4701 **chưa được import vào cột mã nào** (`error_code_c` = 0 dòng toàn DB) |
| Chuỗi lưu thật `C CALL` | **true — thấy trùng** | Khớp đúng chuỗi đã lưu |

→ Chống trùng form ↔ form hoạt động đúng (đã chứng minh #4); form ↔ lịch sử chỉ khớp khi nhập **đúng chuỗi cũ**. Hạn chế dữ liệu lịch sử (không phải lỗi code của vé): nhập lại một ca lịch sử C-call bằng mã thật sẽ **không** bị cảnh báo trùng. Đề xuất: vé sau cân nhắc map cột I vào cột mã khi nhập lịch sử, hoặc mở rộng dedup đối chiếu thêm `no_dvd`/nguồn; tối thiểu ghi nhận là hạn chế đã biết.

## 3. Việc 3 — Cổng kiểm

- `compileall src tests` OK; `check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `cli audit` → `{"status": "PASS", "errors": [], "warnings": []}`; `import aios_habit.workspace_chat_app` → OK; `git diff --check` sạch; `git status --short` sạch.
- Bộ `error_cases` đầy đủ + vé (11 tệp, 161 bài): **160 đạt / 1 đỏ** — đỏ đúng bài va chạm môi trường ở mục 1; 127 bài nền giữ nguyên đạt, 33/34 bài mới của vé đạt (Muse 34/34 trên VM).
- Full suite `pytest -q` (kèm `PYTHONPATH` xlrd + `AIOS_DATA_DIR=C:/tmp/aios-v14-data`; log `C:/tmp/b0-form/full_suite.log`): **3.449 đạt, 2 bỏ qua, 36 lỗi, 4 error** (311,75s) — so nền `date-map` `3.415/2/36/4`: **+34 đạt** (đúng 34 test mới của vé: 33 đạt + 1 đỏ va chạm môi trường).
- Đối chiếu danh sách bài lỗi/error **theo ID** với nền (`C:/tmp/b0-form/compare_failures.py` ↔ `C:/tmp/date-map/after_failures.txt`): 39/40 ID trùng khít; khác biệt đúng 1+1 — **+1** `tests/test_b0_form.py::test_action_no_db_returns_none_and_creates_nothing` (bài va chạm môi trường, mục 1) và **−1** `tests/test_commit_d_wheel_and_packaging.py::TestDesktopPackagingConfiguration::test_packaged_desktop_e2e_rag_to_atlas` (bài nền flaky cần môi trường BGE cách ly — lần này tự xanh). **Không bài nền nào thoái lui.**

## 4. Kết luận / đề nghị

- Tiêu chí vé dành cho OMP ("form chạy được với DB thật, nhập thử 3 ca thật không lỗi") **đạt trên máy nhà**: 3 ca thật ghi thành công đủ trường với DB thật (bản copy), không sinh file rời; chặn thiếu trường bắt buộc; cảnh báo trùng không nhập đúp; mã lạ chỉ cảnh báo; ngày đóng < ngày phát sinh bị chặn; migration cột mới idempotent trên DB cũ thật.
- Hai điểm cần Muse quyết (chi tiết mục 1 và 2.4): (a) 1 bài test đỏ do **va chạm môi trường máy nhà** (đề xuất làm hermetic, không cần sửa sản phẩm); (b) **hạn chế dedup với lịch sử** do cột I chưa được map lúc import.
- Ghi nhận quy trình: `cf730d7` chưa chạm tài liệu canonical nào (`ARCHITECTURE.md` / `PROJECT_HANDOVER.md`) — đề nghị Muse bổ sung mục B0-FORM (form + chat action + cờ `AIOS_FEATURE_CHAT_ACTION`) khi trả verdict; OMP không tự sửa vì lane [VM].
- Ràng buộc giữ: chỉ ghi bản copy ổ C (backup + `integrity_check` trước/sau); không ghi index production; không đụng ổ D (dữ liệu); không merge `main`; không force-push; feature flag mặc định tắt.
