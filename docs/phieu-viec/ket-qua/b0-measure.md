# Vé `B0-MEASURE` — Đo tỉ lệ đủ 5 trường bắt buộc (đóng Bước 0): kết quả

- Trạng thái: **Đo xong trên dữ liệu thật, chờ Muse duyệt.** Kết quả: **cả hai list đều dưới 90%** → chưa đóng được Bước 0 bằng dữ liệu nguồn hiện có; danh sách backfill cụ thể ở mục 6 và các kịch bản quy ước ở mục 7 (Muse quyết).
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (`.venv` của repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `506b38a` (nhận vé + gate ĐẠT) → `c838327` (mốc 2: số đo xong) → (báo cáo này) → (mốc `xong-cho-duyet` theo sau).
- Phạm vi ghi: script + JSON + log trên ổ C (`C:/tmp/b0-measure/`); repo chỉ nhận báo cáo này + `trang-thai.md`. **Không ghi DB gốc, không ghi index production RAG, không đụng ổ D, không merge `main`.**

## 0. Cổng gate (vòng khép kín)

- Vé đúng lane **[NHÀ]**; Muse phát hành trong verdict `B0-DICT` (note 09:47). Điều kiện mở thoả **ngay khi nhận**: cả 2 DB dữ liệu thật sẵn trên máy — list điều tra lỗi 15.707 ca (`C:/tmp/b0-dict/error_cases_dict.db`) và list LSU 23.112 ca (`C:/tmp/lsu1-deploy/error_cases_lsu.db`).
- **Gate ĐẠT — không dùng nhánh “4 lần watcher”/`cho-muse`, không no-op.** (State file của watcher không nằm trong working copy này nên báo cáo không ghi số lần launch; điều kiện mở là yếu tố quyết định và đã thoả ngay.)

## 1. Nguồn đo (chỉ đọc)

| List | DB bản copy trên ổ C | Byte | SHA-256 | Số ca | `integrity_check` |
|---|---|---:|---|---:|---|
| Điều tra lỗi (KDTPS) | `C:/tmp/b0-dict/error_cases_dict.db` | 54.050.816 | `3dad67fe5fa94b3c723cf3e4a4b45ea933ed59dc2d8deeb869d734c6f29e3d97` | 15.707 | ok |
| LSU | `C:/tmp/lsu1-deploy/error_cases_lsu.db` | 26.669.056 | `e24c356a03c4c803379015a05f40e3113be1f7f04d7a6808a9d7a2b86b4cc9c3` | 23.112 | ok |

- Script đo: `C:/tmp/b0-measure/measure.py` (mở `mode=ro`, không ghi DB) + kết quả `measure.json`; script phụ cùng thư mục: `recon.py` (khảo sát), `scan2.py`/`scan3.py`/`scan4.py` (nguồn bù), `variants.py` (kịch bản), `policy.py` (quy ước), `formcheck.py` (đường form) + log `.out.txt`.
- Dùng đúng hàm của sản phẩm: `completeness.is_filled` (chuẩn cổng F3b) và `column_map.extract_code_from_text` (chuẩn B0-DICT) để định nghĩa “có giá trị” và “mã thật”.
- Nguồn gốc: workbook thật `Loi KDTPS.xlsx` sheet `History KDTPS` (15.737 dòng đọc → 15.707 ca) và log LSU thật 888 file/1,21 GB (vé `LSU-1` đã đối chiếu SHA Drive).

## 2. Định nghĩa “5 trường bắt buộc” theo nguồn thật

5 trường bắt buộc (B0-FORM / điều kiện Bước 0): **error code, hiện tượng, nguyên nhân, đối sách, công đoạn**. Đối chiếu header thật hàng 4 của sheet nguồn:

| Trường bắt buộc | Cột nguồn (history_29) | Nhãn nguồn thật | Trạng thái |
|---|---|---|---|
| công đoạn | **F** | 生産工程 / Công đoạn sản xuất | nguồn đầy 99,75% nhưng **chưa được map vào schema** (`process_stage` = 0/15.707) |
| hiện tượng | **I** | 不具合現象 / Hiện trạng lỗi | chứa cả mã thật (B0-DICT trích vào `error_code_i`) |
| error code | G / H / I | (G trống) / 不具合分類 / mã trong text I | H là phân loại lỗi; mã thật nằm trong I |
| nguyên nhân | **AA** | 要因 / Nguyên nhân | 99,95% |
| đối sách | **AB** | 改造 / Kaizo | phần lớn là cờ `要/不要` + `Link(jp+vn)` |

LSU (`lsu_log`): chỉ có hiện tượng (mô tả NG) + khoá log (ngày, jig, serial); **không có cột** mã lỗi (trừ `cam_error` — ERR_NUM), nguyên nhân, đối sách, công đoạn.

Quy ước đo (ghi trong `measure.py`):
- Ô rỗng hoặc placeholder `ー/－/—/–/-/--/ｰ/‐/−///` = **thiếu**.
- `不要` / `要` / `Link(jp+vn)` ở cột AB là **câu trả lời thật** (không tính thiếu); báo cáo kèm số “thô” để đối chiếu cổng F3b.
- “error code” đo **2 cách**: **nới** (có dữ liệu ở ô mã C/H/I) và **chặt** (mã thật trích được từ text = `error_code_i`).

## 3. Kết quả list điều tra lỗi (KDTPS — 15.707 ca)

### 3.1 Từng trường

| Trường | Cách đo | Có giá trị | % | Thiếu | % thiếu |
|---|---|---:|---:|---:|---:|
| error code | nới (C/H/I) | 15.705 | 99,99% | 2 | 0,01% |
| error code | chặt (mã thật) | 3.056 | 19,46% | 12.651 | 80,54% |
| hiện tượng | raw I | 15.674 | 99,79% | 33 | 0,21% |
| nguyên nhân | raw AA | 15.699 | 99,95% | 8 | 0,05% |
| đối sách | raw AB, trừ `ー` | 8.346 | 53,14% | 7.361 | 46,86% |
| công đoạn | raw F | 15.668 | 99,75% | 39 | 0,25% |
| (tham chiếu) công đoạn | cột DB `process_stage` | 0 | 0% | 15.707 | 100% |

- Đối sách “thô” (đếm cả ô `ー`) = 8.912 = **56,74%** — **khớp đúng số cổng F3b** đã có (`fix` 56,7%); nguyên nhân thô 15.699 = 99,9% cũng khớp → số đo nhất quán với công cụ sẵn có.
- Phân bố giá trị AB: `不要` 7.180 · trống 6.795 · `Link(jp+vn)` 1.083 · `ー` 566 · `要` 83. Cột AC (“link báo cáo”) chỉ chứa chữ `LINK (JP+VN)` — **không phải URL/đường dẫn** (1.231 dòng).

### 3.2 Đủ cả 5 trường

| Cách đọc | Số ca | % |
|---|---:|---:|
| Nới (mã = C/H/I) | 8.318 | **52,96%** |
| Chặt (mã thật) | 1.545 | **9,84%** |
| Chặt + trích thêm mã từ cột N/O/L/M/R | 1.850 | 11,78% |

**Kể cả cách đọc rộng nhất, KDTPS chỉ đạt 52,96% < 90%.** Hai nút thắt: **đối sách (thiếu 46,86%)** và **mã thật (thiếu 80,54%)**; các trường còn lại ≤0,25%.

### 3.3 Chi tiết hai trường thiếu nhiều nhất

- **Mã thật (12.651 dòng thiếu)**: trích thêm từ cột N/O/L/M/R (nội dung điều tra/thao tác) được **+531 dòng** → tổng 3.587 = 22,84%. 12.120 dòng còn lại theo phân loại H: `ERROR` 3.537 · `外観` 2.183 · `表示異常` 1.648 · `画像` 1.443 · `機能` 1.021 · `異常音` 776 · `JAM` 622 · `その他` 569 · `C CALL` 351 · `組立` 330 · `治具` 108 · `F CALL` 56 — phần lớn thuộc nhóm khuyết điểm **không có mã trong nguồn**.
- **Đối sách (7.361 dòng thiếu)**: 100% dòng này **có** cột M/O “nội dung thao tác khi phát sinh” (hành động tức thời, không phải đối sách chính thức), 7.329 dòng có cột N; 1.511 dòng trong nhóm có mã thật; 5.850 dòng thiếu cả mã lẫn đối sách (37,24%).
- 33 dòng thiếu hiện tượng (chủ yếu 2026/2xxx), 8 dòng thiếu nguyên nhân, 39 dòng thiếu công đoạn — danh sách `no_dvd` cụ thể nằm trong log đo (`scan4.out.txt`).

## 4. Kết quả list LSU (23.112 ca)

| Trường | Nguồn đo | Có giá trị | % | Thiếu | % thiếu |
|---|---|---:|---:|---:|---:|
| error code | `error_code_h` (chỉ cam_error ERR_NUM) | 1 | 0,004% | 23.111 | 99,996% |
| hiện tượng | `investigation` | 23.112 | 100% | 0 | 0% |
| nguyên nhân | raw `cause` (luôn rỗng) | 0 | 0% | 23.112 | 100% |
| đối sách | raw `fix` (luôn rỗng) | 0 | 0% | 23.112 | 100% |
| công đoạn | (không có cột nguồn) | 0 | 0% | 23.112 | 100% |
| **đủ 5 trường** | | **0** | **0%** | 23.112 | 100% |

Theo định dạng: `jig_result` 7.535 · `unit_judge` 12.893 · `unit_result` 2.683 · `cam_error` 1 — mọi định dạng đều 0% ở 4 trường ngoài hiện tượng. Log vận hành chỉ mang “cái gì NG, lúc nào, ở đâu”, không mang nguyên nhân/đối sách — khớp kết luận vé `LSU-1` (gate F3b cause/fix 0%).

## 5. Tài liệu thật có thể bù (đã kiểm kê)

- **Theo mã (bù cho KDTPS)**: `Lịch sử lỗi/C Call/` — 231 mục, gồm **217 file `KTD-*.xlsx`** (báo cáo từng ca; tên file mang mã + line + công đoạn, ví dụ `KTD-2024-11-1537-Iris2020-C34-A1-C7901.xlsx`) + 11 thư mục theo mã (`6620`, `7303`, `C0650`, `C1905`, `C2300 PQC`, `C2310`, `C2500`, `C3501`, `C6610`, `C6900`, `C9540`) chứa `.msg/.xlsx/.log/.pdf`; `Lịch sử lỗi/Log/` — 5 thư mục mã + PDF báo cáo ca (`KTD-…-C0363/C1950/C4001/C6770/C9540`).
- **Theo cụm (bù cho LSU)**: biên bản họp chất lượng `RE_ Iris LSU Beam径NG多発 異常品質会議 {2,3,5}回目.msg`, báo cáo `Sirius 2 _ C7620_報告版 4.pptx`, `Y_BeamH_Camera 140_to bất thường.pptx`, các bảng tổng hợp thí nghiệm `tổng hợp dữ liệu*.xlsx` trong `6thA3 LSU/Lỗi JIG BEAM/`.
- **Từ điển**: `Bang ma loi/` (6 file) — đã nhập bởi B0-DICT (3.839 mục); 87 mã còn thiếu tra được (41 C + 46 F) thuộc phạm vi vé B0-DICT/Muse quyết.
- **Đường dữ liệu mới**: 4/4 ca nhập qua form B0-FORM (`C:/tmp/b0-form/error_cases_form.db`, `FORM-20261001-0001..0004`) **đủ cả 5 trường** — dữ liệu mới đạt chuẩn theo thiết kế; vấn đề nằm ở dữ liệu lịch sử.

## 6. Danh sách backfill cụ thể (đề xuất vé tiếp theo — Muse quyết)

| # | Trường | Thiếu | Nguồn BÙ được (làm tự động/qua code) | Nguồn CHỊU (cần người/quy ước) | Ước lượng sau bù |
|---|---|---|---|---|---|
| 1 | công đoạn (KDTPS) | 39 dòng nguồn (DB đang 0%) | Cột F đã đầy 99,75% → vé [VM] map `F → process_stage` + backfill kiểu `backfill_error_code_i` (dry-run → apply trên bản copy) | 39 dòng F trống → rà soát tay | **99,75%** (từ 0% ở cột DB) |
| 2 | mã lỗi thật (KDTPS) | 12.651 | +531 dòng trích từ cột N/O/L/M/R (mở rộng `extract_code_from_text` + backfill) | 12.120 dòng còn lại: chốt quy ước “ca không có mã” (nhóm `外観/画像/異常音…`) hoặc bắt buộc nhập mã khi đóng phiếu (B2) | 22,84% (auto), phần còn lại theo quy ước |
| 3 | đối sách (KDTPS) | 7.361 | 217 file `KTD-*.xlsx` + thư mục mã trong `C Call`/`Log` — đối chiếu **theo mã** (pilot N file rồi mở rộng) | 6.795 ô trống + 566 `ー`: rà soát dùng M/O (đã có 100%) + chốt quy ước `不要`/“không cần đối sách”; 1.083 dòng `Link(jp+vn)` cần người gửi tài liệu JP+VN thật | phụ thuộc rà soát |
| 4 | hiện tượng / nguyên nhân (KDTPS) | 33 / 8 | — | rà soát tay 41 dòng (danh sách trong log đo) | 100% |
| 5 | LSU (mã / công đoạn / nguyên nhân / đối sách) | ~100% cả 4 trường | Ca **mới**: form B0-FORM (đã đo 4/4 đủ 5 trường) | 23.112 sự kiện lịch sử: biên bản/họp chất lượng (`.msg`) + báo cáo (`.pptx`) + rà soát theo cụm (dialect/jig/ngày) — **cần người dùng** | không tự động được |

## 7. Kịch bản theo quy ước (để Muse chốt cách đọc điều kiện ≥90%)

| Cách đọc | KDTPS | LSU |
|---|---:|---:|
| Chặt: mã thật + đối sách đã ghi (trừ `ー`) | 9,84% | 0% |
| Nới: mã C/H/I + đối sách đã ghi (kể cả `不要`/`Link`) | 52,96% | 0% |
| Quy ước: ô đối sách trống = “không cần đối sách” (cần user xác nhận) | **99,48%** | 0% |

→ Điều kiện ≥90% **phụ thuộc 2 quyết định chính sách** (mã cho ca không có mã; nghĩa ô đối sách trống trong lịch sử) **và** việc sửa mapping công đoạn. Không có kịch bản nào đạt cho **list LSU** nếu không có rà soát của người dùng.

## 8. Cổng nền

- `uv run --no-sync --group dev python -m compileall -q src tests` → **OK**.
- `PYTHONPATH='src' uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"`, `errors`/`warnings` rỗng.
- `PYTHONPATH='src;C:/tmp/e3-py311' uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → **IMPORT_OK**.
- Full suite: `AIOS_DATA_DIR='C:/tmp/aios-v14-data' PYTHONPATH='src;C:/tmp/e3-py311' TMP=TEMP='C:/tmp' uv run --no-sync --group dev python -m pytest -q` → **3.474 đạt / 2 bỏ qua / 35 lỗi / 4 error** (605,03s) — **trùng khít nền vé trước (`B0-DICT`: 3.474/2/35/4), không thoái lui**. 4 error đều ở `tests/test_chat_action_error_lookup.py` (hardcode đường dẫn VM `/home/hatch/...`, lane [VM] của B1-FEAT — đã biết từ vé `LSU-1`). 35 lỗi: graphify ×9, BGE worker/client ×9, wheel/packaging (`commit_d`) ×3, rag_v2 (dev_cli/eval_harness/synthesis) ×4, còn lại 10 bài lẻ nền có sẵn (chunk_evaluation, commit_b tier5, chat_action_error_lookup, expert_knowledge_e2e, mom_pilot, notebook, owner_pilot, 2 bài adapter/owner-flow workspace-chat, antigravity) — **không bài nào thuộc phạm vi vé này** (vé không đổi code).

## 9. Ràng buộc vé — đều giữ

- **Không ghi DB gốc**: mọi lần mở DB ở `mode=ro`; không UPDATE/INSERT/DELETE; `integrity_check` ok trên cả 2 DB (ghi ở mục 1).
- **Không ghi index production RAG**, không nhúng vector, không mở `library.sqlite` nào.
- **Không đụng ổ D**: dữ liệu chỉ đọc từ bản copy trên ổ C (`C:/tmp/...`).
- **Không merge `main`**, không force-push; chỉ push nhánh `phieu-viec/rag-fix1`.
- **Dữ liệu thật không vào Git**: báo cáo chỉ có số liệu + đường dẫn ổ C + nhãn/mã nghiệp vụ (không dán nội dung dài từ nguồn).

## 10. Ghi chú và hạn chế

- Số đo theo **nguồn raw_json** (cùng cách tiếp cận cổng F3b) — cột DB mới của form (`phenomenon`, `cause`, `countermeasure`, `process_stage`) hiện chỉ có dữ liệu ở các dòng nhập form (4 ca), không ảnh hưởng số đo lịch sử.
- Cột AB/AC là **cờ nghiệp vụ**, không phải nội dung/URL → không thể tự động trích “đối sách” từ chúng.
- Danh sách 217 file `KTD-*` chỉ được **kiểm kê + ví dụ tên**; cấu trúc bên trong chưa khảo sát (việc của vé backfill nếu Muse phát hành).
- Ước lượng sau bù ở mục 6 là **trần lý thuyết** theo nguồn đã kiểm kê, chưa gồm sai số trích xuất tài liệu.
- `C:/tmp/b0-dict/error_cases_dict.db` là bản copy đã qua migrate + backfill của B0-DICT (khác SHA bản `date-map`); SHA ghim ở mục 1 là SHA tại thời điểm đo.

## Kết luận

Vé `B0-MEASURE` **hoàn tất phần thực thi**: con số đo thật trên cả 2 list là **KDTPS 52,96% (nới) / 9,84% (chặt)** và **LSU 0%** — đều **< 90%**, nên Bước 0 **chưa đóng**; báo cáo kèm danh sách backfill cụ thể theo từng trường (mục 6), tài liệu thật có thể bù (mục 5), các kịch bản quy ước (mục 7) và bằng chứng cổng nền (mục 8). Chờ Muse review + verdict.
