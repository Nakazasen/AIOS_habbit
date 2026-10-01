# Vé `B1-FEAT` — Bước 1 thành tính năng hoàn chỉnh: kết quả verify trên máy nhà

- Trạng thái: **Verify xong trên dữ liệu thật, chờ Muse duyệt.** Kết luận: **ĐẠT cả 4 tiêu chí của vé trên cả 2 đường DB** — (1) DB làm việc `C:/tmp/b0-dict/error_cases_dict.db` (đủ cột, xếp hạng QĐ1 kích hoạt) và (2) **đường mặc định sản phẩm** `C:/tmp/buoc0-deploy/error_cases_deploy.db` (schema cũ) **sau bản vá `bf33ac0`** của Muse — vá đúng phát hiện chặn ghi ở Mốc S1 (mục 3).
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (`.venv` của repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `58a6231` (nhận vé + gate ĐẠT) → `051ffef` (mốc S1: smoke + phát hiện chặn) → `bf33ac0` (Muse vá) → `7d06e51` (mốc S2: cổng nền, sau rebase kèm vá) → (báo cáo này) → (mốc `xong-cho-duyet` theo sau).
- Phạm vi ghi: script + JSON + log trên ổ C (`C:/tmp/b1-feat/`); repo chỉ nhận báo cáo này + `trang-thai.md`. **Không ghi DB (mở `mode=ro`), không ghi index production RAG, không nhúng vector, không đụng ổ D, không merge `main`, dữ liệu thật không vào Git.**

## 0. Cổng gate (vòng khép kín)

- Phiên này do watcher tự mở lúc **10:34:57** (`LAUNCH 1/4` chu kỳ mới; sig đổi sang `4c083b1` vì Muse báo code xong trong commit `fcaaa06`; hai lần trước 10:12/10:23 là chu kỳ cũ chưa có điều kiện mở). **Gate ĐẠT — không dùng nhánh “4 lần watcher”/`cho-muse`, không no-op.**
- Vòng khép kín hoạt động đúng: OMP báo chặn ở Mốc S1 (10:44) → **Muse vá `bf33ac0` + ghi chú 10:55** → OMP verify lại và hoàn tất. State/log watcher nằm ngoài working copy (`D:/Sandbox/Vong_lap_giao_viec/`).

## 1. Nguồn verify (chỉ đọc)

| Nguồn | Đường dẫn | Byte | SHA-256 | Ghi chú |
|---|---|---:|---|---|
| DB b0-dict (có `error_code_i`) | `C:/tmp/b0-dict/error_cases_dict.db` | 54.050.816 | `3dad67fe5fa94b3c723cf3e4a4b45ea933ed59dc2d8deeb869d734c6f29e3d97` | 15.707 ca; batch `Loi KDTPS.xlsx › History KDTPS` |
| DB deploy (mặc định sản phẩm) | `C:/tmp/buoc0-deploy/error_cases_deploy.db` | 49.881.088 | `fa9efeba5693df18e49341067cce49293895f00dc71c5d2dc7b7222c294946d8` | cùng 15.707 ca; schema cũ, **không** có `error_code_i` |
| DB LSU | `C:/tmp/lsu1-deploy/error_cases_lsu.db` | 26.669.056 | `e24c356a03c4c803379015a05f40e3113be1f7f04d7a6808a9d7a2b86b4cc9c3` | 23.112 ca (chỉ dùng đối chứng) |
| Workbook nguồn thật | `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/Loi KDTPS.xlsx` | 10.006.929 | — | sheet `History KDTPS` (15.741 dòng) |

- Script smoke: `C:/tmp/b1-feat/verify_b1_feat.py` (throwaway) → `verify_b1_feat_result_pre_fix.json` (trước vá) + `verify_b1_feat_result.json` (sau vá); script phụ `probe_xlsx_rows.py`, `inspect_db.py`.
- Đường chạy đúng sản phẩm: `chat_action.handle_chat_text` — chính hàm `workspace_chat_app.py:3903` gọi khi cờ `AIOS_FEATURE_CHAT_ACTION=1` (bật trong tiến trình script). Nhập mã trần → `match_action` chọn action `tra_cuu_loi_tuong_tu` → handler render thẻ ngay trong cùng lượt (không rơi xuống luồng RAG hỏi lại).
- Mức verify UI: không lái được widget Streamlit bằng automation (giới hạn đã ghi từ vé `move-index-c`); mức tương đương = gọi đúng hàm cửa vào mà app dùng.

## 2. Tiêu chí vé — 5 mã lỗi thật (ĐẠT)

5 mã thật: `F000`, `C7620`, `C3200`, `C4701` (trùng bộ mã test VM) + `C0840` (thay `C0030` — `C0030` chỉ có trong từ điển glossary, **0 ca lịch sử** trên dữ liệu nhà nên không thể ra thẻ).

### 2.1 Trên DB b0-dict (đủ cột `error_code_i` — xếp hạng QĐ1 kích hoạt)

| Mã | Thẻ | Giây | 4 trường | Nguồn `Loi KDTPS.xlsx` | Thẻ đầu |
|---|---:|---:|---|---|---|
| `F000` | 5 | 0,17 | đủ | ✓ | Phiếu 2023/384 · Libra / A23 · F CALL |
| `C7620` | 5 | 0,11 | đủ | ✓ | Phiếu 2023/102 · Iris2020 下位 / C34 · C CALL |
| `C3200` | 5 | 0,11 | đủ | ✓ | Phiếu 2024/3667 · Iris2020 下位 / C35 · C CALL |
| `C4701` | 5 | 0,11 | đủ | ✓ | Phiếu 2023/1203 · Iris2020 下位 / C34 · C CALL |
| `C0840` | 5 | 0,12 | đủ | ✓ | Phiếu 2023/660 · Iris2020 Mono / C35 · C CALL |

- **Tổng 0,62 giây cho 5 mã** (< 1 phút — đạt xa ngưỡng vé). Kết quả không đổi trước/sau bản vá (đo 2 lần, cùng số).
- **QĐ1**: top-5 của cả 5 mã đều là ca có mã thật (`co_ma_that=True` ×5), thứ tự hợp lệ trên dữ liệu thật.
- **Không hỏi ngược**: `handle_chat_text` trả `True` ngay cho mã trần — không rơi về luồng RAG.

### 2.2 Trên đường mặc định sản phẩm (deploy DB, schema cũ) — sau bản vá `bf33ac0`

| Mã | Thẻ | Giây | 4 trường | Nguồn `Loi KDTPS.xlsx` |
|---|---:|---:|---|---|
| `F000` | 5 | 0,12 | đủ | ✓ |
| `C7620` | 5 | 0,11 | đủ | ✓ |
| `C3200` | 5 | 0,11 | đủ | ✓ |
| `C4701` | 5 | 0,11 | đủ | ✓ |
| `C0840` | 5 | 0,11 | đủ | ✓ |

- **Tổng 0,58 giây cho 5 mã.** Trước bản vá đường này **không ra thẻ** (5/5 fallback im lặng) — xem mục 3.
- **QĐ1 trên schema cũ**: `co_ma_that` toàn `False` (DB cũ chưa có cột mã thật và `error_code_c` trống) → không có gì để xếp hạng; tính năng vẫn trả lời đủ 5 thẻ. Khi vé `BK-ERRCODE` backfill mã thật (hoặc DB được migrate B0-DICT), QĐ1 sẽ kích hoạt trên đường này.

### 2.3 Kiểm chung (cả 2 DB)

- **Link báo cáo gốc mở được**: provenance `Loi KDTPS.xlsx › History KDTPS › dòng N`; kiểm chéo bằng openpyxl trên workbook thật — cả 5 thẻ top-1 khớp **offset 0** (F000→dòng 6 `LCD画面にF000表示`; C7620→106; C3200→337; C4701→1207; C0840→478).
- **QĐ2**: quét toàn DB b0-dict — **7.361 dòng** ô `AB` trống/`ー` có M/O → render đúng `Không cần đối sách chính thức`; **0 dòng** trống AB mà không có M/O (khớp ghi chú skip của test VM — dữ liệu thật không có ca này).
- **Ràng buộc `mode=ro`**: SHA-256 + mtime của cả 3 DB **không đổi** sau toàn bộ smoke; không sinh `.wal/.shm/.journal`.
- **Fail-closed**: thiếu DB (env rỗng + defaults trỏ đường không tồn tại + context sai — mô phỏng trong tiến trình) → `False`; DB rỗng → `False`. Không crash, không lộ traceback.

## 3. Phát hiện chặn (Mốc S1) và bản vá `bf33ac0`

- **Trước bản vá**, trên DB deploy (schema cũ): 5/5 mã → `handle_chat_text` trả `False`, 0 thẻ — `search_similar` ném `IndexError: No item with that key` tại `_has_real_code` (dòng 202: đọc `row["error_code_i"]` không guard), bị `_handler` `except Exception` (dòng 500-501) nuốt → fallback im lặng. Không nhất quán với `_candidate_rows` (dòng 211) vốn đã có guard `_has_error_code_i` cho DB cũ.
- **Bằng chứng cô lập** (trước vá): patch tạm `_has_real_code` trong tiến trình smoke → `F000` ra ngay 5 ca → nút thắt đúng 1 chỗ.
- **Muse vá `bf33ac0`** (10:54): bọc `error_code_c`/`error_code_i` bằng `try/except (KeyError, IndexError, TypeError)` — đúng style guard `code_missing` sẵn có; thêm test hồi quy `test_search_similar_old_schema_without_error_code_i` (drop cột → không ném, vẫn ra thẻ). Muse chạy lại file test trên VM: 17 đỗ/1 skip.
- **Verify lại sau vá (OMP, máy nhà)**: deploy DB 5/5 mã → 5 thẻ/0,58 s (mục 2.2); gọi trực tiếp `search_similar` trên DB cũ không còn ném; hành vi trên DB b0-dict không đổi (mục 2.1).

## 4. Ràng buộc đã giữ

- **Không ghi DB gốc**: mọi lần mở DB ở `mode=ro`; SHA-256 + mtime 3 DB không đổi sau toàn bộ quá trình; không sinh file WAL/journal.
- **Fail-closed** giữ nguyên (thiếu/rỗng → action không trả thẻ, app rơi về RAG — không vỡ).
- **Không ghi index production RAG**, không nhúng vector, không mở `library.sqlite` nào.
- **Không đụng ổ D**: script + log + JSON chỉ trong `C:/tmp/b1-feat/`.
- **Không merge `main`**; chỉ push nhánh `phieu-viec/rag-fix1`.
- **Dữ liệu thật không vào Git**: báo cáo chỉ có số liệu + đường dẫn + mã nghiệp vụ ngắn (không dán nội dung dài từ nguồn).

## 5. Cổng nền

- Bốn cổng nhanh (sau vá): `compileall -q src tests` **PASS** · `check_docs.py` **DOCUMENTATION_CONTRACT=PASS** · `aios_habit.cli audit` **`"status": "PASS"`** · import `workspace_chat_app` **OK**.
- Full suite (đúng lệnh nền `AIOS_DATA_DIR='C:/tmp/aios-v14-data' PYTHONPATH='src;C:/tmp/e3-py311' TMP=TEMP='C:/tmp'`):
  - **Trước vá** (`4c083b1`): **3.475 đạt / 2 bỏ qua / 34 lỗi / 9 error** (516 s) — log `pytest_full2.log`.
  - **Sau vá** (`bf33ac0`): **3.475 đạt / 2 bỏ qua / 35 lỗi / 9 error** (523 s) — log `pytest_full3.log`. Bản vá thêm 1 test hồi quy **đạt** (`test_search_similar_old_schema_without_error_code_i`); đồng thời 1 bài cũ `test_missing_db_returns_none` chuyển đạt→lỗi **trên máy nhà**: trước vá nó “đạt nhờ bug” (fallback nuốt `IndexError` → `None`), sau vá đường mặc định (`C:/tmp/buoc0-deploy/error_cases_deploy.db` có thật trên máy) trả outcome → `assert ... is None` hỏng. Bài test giả định môi trường **không có DB mặc định** → **giới hạn portable của test, không phải lỗi sản phẩm** (hành vi đúng ở mục 2.2; ca “thiếu DB” được kiểm bằng mô phỏng ở mục 2.3; trên VM bài này đạt — khớp 17 đỗ/1 skip của Muse).
  - So nền B0-DICT trong mailbox (3.474/2/35/4): tổng +5 test = đúng 5 test mới của vé (đo trực tiếp trên máy nhà: file test vé 12 bài → 8 đạt/4 error; 17 bài → 8 đạt/9 error; sau vá 18 bài → 8 đạt + 1 lỗi (`test_missing_db_returns_none`) + 9 error — 9 error đều do fixture hardcode đường dẫn VM `/home/hatch/...`, lane [VM]); danh sách lỗi trùng đúng các nhóm nền (graphify 9, BGE worker/client 9, commit_d 3, rag_v2 4, còn lại bài lẻ), **không nhóm lỗi mới** ngoài 2 hiện tượng đã giải thích ở trên.
  - Ghi chú môi trường (cho các phiên sau): thiếu `xlrd` → 12 file lỗi collection (`xlrd` thuộc group tùy chọn `rag-ingestion-xls`, không có trong venv; dùng `C:/tmp/e3-py311`); thiếu `AIOS_DATA_DIR`/`TMP` → 25 skip + 15 error giả.
- Đối chứng cây cha `4c083b1^` (worktree riêng ổ C:, cùng lệnh): **3.483 đạt / 3 bỏ qua / 25 lỗi / 4 error** — chênh 9 bài `bge_subprocess_worker/client` (pass trên worktree, fail trên cây chính `D:` — nhóm nền flaky theo môi trường cây, fail cả trước lẫn sau vé trên cây chính) → không do code vé (log `pytest_parent.log`).

## 6. Kết luận & đề xuất cho Muse

1. **ĐẠT tiêu chí vé** trên cả 2 đường DB sau bản vá: 5/5 mã → top 3–5 thẻ, đủ 4 trường + nguồn mở được, ≤0,62 s, không hỏi ngược; QĐ1/QĐ2 đúng trên DB đủ cột; fail-closed + `mode=ro` giữ nguyên.
2. Ghi chú cho các vé sau (không chặn gì):
   - Trên DB deploy schema cũ, **xếp hạng QĐ1 chưa kích hoạt** (chưa có mã thật) — vé `BK-ERRCODE`/migrate B0-DICT sẽ bổ sung.
   - Test file vé chưa portable sang máy nhà: hardcode dữ liệu VM (`/home/hatch/...`) → error 9 bài; `test_missing_db_returns_none` giả định thiếu DB mặc định → fail khi máy có `C:/tmp/buoc0-deploy/error_cases_deploy.db` (trước vá “đạt nhờ bug”). OMP đã thay bằng smoke dữ liệu thật (mục 2). Nếu muốn chạy đa máy: dùng cơ chế env kiểu `AIOS_DATA_DIR` + che/patch default candidates trong test.
3. Không đề xuất thao tác ghi/ migrate DB nào trong phạm vi vé — mọi thứ chỉ đọc.

## 7. Phụ lục — bằng chứng thô

- Script + kết quả: `C:/tmp/b1-feat/verify_b1_feat.py`, `verify_b1_feat_result_pre_fix.json`, `verify_b1_feat_result.json`, `probe_xlsx_rows.py`, `inspect_db.py`.
- Log suite: `C:/tmp/b1-feat/pytest_full2.log` (trước vá), `pytest_full3.log` (sau vá), `pytest_parent.log` (đối chứng cây cha `4c083b1^`, worktree riêng).
- Commit code được verify: `4c083b1` (QĐ1+QĐ2) + `bf33ac0` (vá guard schema cũ); đỉnh nhánh lúc báo cáo: `7d06e51`.
