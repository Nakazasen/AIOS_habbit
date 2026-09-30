# Vé `LSU-1` — Chạy pipeline Bước 0–5 trên list LSU thật: nghiệm thu

- Trạng thái: **Pipeline chạy xong, exit 0 — chờ Muse duyệt** (toàn bộ số liệu trong báo cáo là đo thật).
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (`.venv` của repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `d68ccef` (nhận vé) → `c0cbd5b` (code importer) → `b4e2250` (mốc 1) → `ef26681` (mốc 2) → `0efa91a` (mốc 3) → `38f7e05` (báo cáo + trang-thai) → `276d7d7` (fix digest dòng nguồn).
- Phạm vi ghi: dữ liệu + DB + output + log trên ổ C (`C:/tmp/lsu1-deploy/`); repo chỉ nhận code + test + báo cáo + `trang-thai.md`. **Không ghi ổ D, không ghi index production RAG, không merge `main`.**

## 0. Cổng gate + cách hiểu “list LSU” (đối chiếu vé)

**Cổng gate ĐẠT — không dùng nhánh “4 lần watcher”:** watcher tự mở OMP **1/4** lần cho vé này; điều kiện mở đã thoả ngay: (a) GPU-DC đã ĐẠT (`805392f`); (b) dữ liệu LSU có sẵn cả trên ổ D (`Tài liệu của tất cả dòng máy`) lẫn bản công khai trên Drive `AIOS_Data` (đã kiểm chứng đọc ẩn danh trước khi nhận vé); (c) ổ C trống ~12 GB; (d) Python 3.11.14 sẵn sàng. Vé tiếp tục bình thường, **không no-op, không chuyển `cho-muse`**.

**“List LSU (log jig, log 6 pcs theo chuỗi, tài liệu LSU)”** = bộ dữ liệu LSU thật của 3 dòng máy trong `Tài liệu của tất cả dòng máy`, gồm:

| Thư mục | Nội dung | Vai trò trong vé |
|---|---|---|
| `6thA3 LSU/Lỗi JIG BEAM/` | “log jig”: `Log2021_*.csv` (SelNo/Date/Time/JigNo/FinTest + ma trận đo) | Bước 1 — nhập sự kiện NG |
| `Iris LSU/log/`, `Iris LSU/thu nghiem 6pcs do thong so va log/` | “log 6 pcs theo chuỗi”: `*_UnitTest.csv`, `2026_08.csv`, `2026_08_Error.csv`, `*_CamError.csv`, `*_Depth/Profile/Spec/CamPos.csv` | Bước 1 — nhập sự kiện NG (Depth/Profile là ma trận đo, không phải sự kiện) |
| `Sirius LSU/` | log bộ kiểm UnitTest/judge + ma trận đo của các bước linearity | Bước 1 — nhập sự kiện NG |
| `LSU UNIT (V) Lần 2.ppt(x)`, `Tài liệu đào tạo LSU_2019.01.18_K.pptx` | “tài liệu LSU” | Kiểm kê + SHA (kho số hóa để vé sau) |
| 545 file Depth/Profile/Spec/CamPos + ảnh/DB (`Thumbs.db`, `*.db`, `*.png`) | ma trận số đo thô, không mang trạng thái lỗi | **Không nhập** (lý do ở mục 8) |

## 1. Bước 1 — Dữ liệu ra ổ C + đối chiếu SHA-256

- Copy chỉ-đọc từ ổ D sang `C:/tmp/lsu1-deploy/data/lsu` (**không ghi ổ D**):

| Nguồn (D:) | File | Byte |
|---|---:|---:|
| `6thA3 LSU` | 82 | 33.250.044 |
| `Iris LSU` | 61 | 273.827.843 |
| `Sirius LSU` | 742 | 890.098.374 |
| 3 tài liệu LSU (ppt/pptx/pptx) | 3 | 14.396.313 |
| **Tổng** | **888** | **1.211.572.574** |

- Manifest SHA-256 từng file: `C:/tmp/lsu1-deploy/lsu_manifest.json` (SHA-256 `7a20251e…e4448f`).
- **Đối chiếu Drive AIOS_Data công khai: 7/7 mẫu khớp SHA-256 + kích thước** (`drive_verify.json`, SHA-256 `760e1f7c…`): đủ 4 định dạng log của cả 3 dòng máy + 1 tài liệu; tải bằng kênh ẩn danh `drive.google.com/uc?export=download` và so từng byte với bản C:.

Chưa thấy “gói LSU” trong `C:/tmp/aios-v14-data/`; nguồn Drive đã dùng đúng như vé chỉ dẫn (thư mục LSU trong `AIOS_Data`).

## 2. Bước 2 — Mở rộng importer cho định dạng log LSU (code + test, commit riêng)

Commit code: **`c0cbd5b`** + fix **`276d7d7`** (digest dòng nguồn phủ toàn bộ ô đọc được — log thật có dòng dài hơn header; kèm test hồi quy) — module mới `src/aios_habit/error_cases/import_lsu_logs.py` (+ mở rộng additive `completeness.py` / `store.py` / `__init__.py`). Quy tắc sự kiện và ánh xạ:

| Định dạng | Nhận diện header | Sự kiện = | Ghi chú |
|---|---|---|---|
| `cam_error` | `DATE,TIME,CAM_ID,ERR_NUM` | mọi dòng (log lỗi camera) | mã lỗi = `ERR_NUM` → `error_code_h` |
| `jig_result` | `SelNo,Date,Time,JigNo,FinTest` | `FinTest` khác `OK`/rỗng | “log jig” 6thA3 |
| `unit_judge` | có cột chứa `judge` (`TotalJudge`, `Black_TotalJudge`, `Judge:Black`…) | bất kỳ cột judge nào = `NG` | Iris + Sirius |
| `unit_result` | cột `RESULT` / `RESULT:<MÀU>` | bất kỳ cột result nào = `NG` | Iris |

- Ánh xạ vào `error_cases` (provenance-first): `no_dvd = "LSU/{đường_dẫn_tương_đối_bỏ_đuôi}/{dòng}"` (log không có số phiếu); `machine_type = "LSU"`; `line` = họ sản phẩm theo thư mục gốc (`6thA3` / `Iris` / `Sirius`); `investigation` = mô tả hiện tượng tiếng Việt (cột nào NG / FinTest / CamError); `cause/fix/department/handler` để trống đúng thực tế.
- `raw_json` gọn (`format=lsu_log`, dialect, ngày, cột khoá + cột kết quả, `columns_total`, **`row_sha256`** = digest toàn dòng nguồn join `\x1f`) — không nhân bản ma trận tới 992 cột (ước tính +563 MB vô ích); tệp gốc còn nguyên trên đĩa nên tái lập được từng dòng. Header thật có khoảng trắng đầu cột không nhất quán (`' DATE'`, `' S/N'`) — mọi ánh xạ đi qua chuẩn hoá.
- Chống nhập trùng: cùng (tệp, sha256, dialect) bị bỏ qua, `force=True` ghi lại vào đúng batch; ghi vào đúng batch gốc nếu chạy lại.
- Test mới (fixture tổng hợp, **không dùng dữ liệu công ty**): `tests/test_error_cases_lsu_logs.py` — 12 bài. Bộ `error_cases` đầy đủ: **105/105 đạt** (93 bài cũ + 12 bài mới) trên Windows Python 3.11 với `AIOS_DATA_DIR=C:/tmp/aios-v14-data`, `PYTHONPATH=C:/tmp/e3-py311`.
- Smoke trên dữ liệu thật: 238 file nhận dạng / **23.112 sự kiện**; 3/3 mẫu đối chiếu digest dòng nguồn khớp lại từ tệp gốc.

## 3. Bước 3 — Chạy pipeline Bước 0–5 trên dữ liệu LSU thật

Runner: `C:/tmp/lsu1-deploy/run_lsu_pipeline.py` (script tạm trên ổ C, không commit — như `buoc0-deploy`). Chạy `2026-10-01 03:58:09 → 04:01:06` (~177 giây), **exit code 0**, `tong_ket.json` = `"tat_ca_buoc": "OK"`.

| Mốc | Việc đã chạy | Kết quả thật |
|---|---|---|
| Bước 0 (nền) | schema + nạp 4 bảng mã lỗi thật vào từ điển (cùng bộ với `buoc0-deploy`) | C_CALL 226 + F_SYSTEM 127 + SCT_ADJ 37 + JAM 3.430 = **3.820 mục**; tra thử C0030 → “Bất thường hệ thống bản mạch FAX” |
| Bước 1 (nhập + gate F3b) | `import_lsu_tree` quét 783 CSV, nhập 238 file nhận dạng | **137.498 dòng đọc → 23.112 ca nhập** (114.386 dòng là số đo OK, không phải sự kiện); phân bố: jig_result 7.535 ca/20 file, unit_judge 12.893/210, unit_result 2.683/7, cam_error 1/1; theo dòng máy: 6thA3 7.535, Iris 8.993, Sirius 6.584. 545 file không nhận dạng (Depth/Profile/Spec/CamPos…). **Gate F3b FAIL đúng thực tế**: trường lõi `cause`/`fix` = **0%** (log không mang nguyên nhân/đối sách); `no_dvd`/`machine_type`/`line`/`date`/`investigation`/`source_row` = 100%; `department`/`handler` = 0% (ngoài lõi) → mở vé F3b backfill cho list LSU |
| Bước 2 (feedback loop) | 3 ca thật (cam/jig/judge): gọi gợi ý → đánh giá → đóng phiếu | coverage **1,0 (3/3)**; đóng 1 ca thành công với nguyên nhân/đối sách gắn nhãn `SIMULATED_*`; **chặn đúng** khi thiếu đối sách: “Không đóng được phiếu: thiếu đối sách thật (actual_countermeasure).”; positive theo quý 3/3 |
| Bước 3 (cây điều tra) | hiện tượng thật lấy từ ca `LSU/6thA3 LSU/Lỗi JIG BEAM/2021.03.26/Log2021_3/120` | “Lỗi JIG BEAM: FinTest=NG (JigNo=#1, SelNo=E9L119174234)” → **4 nhánh 4M + 16 checklist + 5 cấp Why-Why** → `out/buoc3_cay_dieu_tra.md` |
| Bước 4 (xu hướng) | `run_periodic_report` trên 23.112 bản ghi (Model/Line/Công đoạn) | **6 dòng cảnh báo** vượt ngưỡng 20% (kỳ 2026-W40): Model=LSU 100%, Line 6thA3 32,6% / Iris 38,9% / Sirius 28,5%, Công đoạn #1 34,5% / “(không rõ)” 57,8% → `out/buoc4_bao_cao_xu_huong.md` |
| Bước 5 (phân loại + tái phát) | phân loại mã thật + so lịch sử + đo độ chính xác | độ chính xác tập `SIMULATED_*` (n=12): 1,00/1,00/1,00; phân loại mã thật `-1306` → nhóm `linh_kien`, conf 0,55, 5 match lịch sử; cảnh báo tái phát `-1306` (1 bản ghi trong DB) kèm đối sách gợi ý |

Output trên ổ C (SHA-256 để Muse audit):

| File | Byte | SHA-256 |
|---|---:|---|
| `error_cases_lsu.db` | 26.669.056 | `e24c356a…4cc9c3` |
| `tong_ket.json` | — | `9b031095…fc02456b` |
| `out/buoc1_gate_f3b.md` | — | `1037e563…eee8539e` |
| `out/buoc3_cay_dieu_tra.md` | — | `ed770198…235283893` |
| `out/buoc4_bao_cao_xu_huong.md` | — | `26f22ccd…2deb7b4` |
| `scan_lsu.json` (quét toàn bộ 783 CSV trước khi thiết kế importer) | — | `dcb62e85…a4430318` |

## 4. Bước 4 — Kiểm tra output: đúng format, đủ mốc, không exception

- **Đúng format**: runner assert từng file output — gate F3b (bảng trường + dòng gate), cây điều tra (đủ mục “1. Cây điều tra 4M” + “2. Chuỗi Why-Why”), báo cáo xu hướng (đủ “Bảng tỉ lệ phát sinh” + “Cảnh báo”) — tất cả đạt.
- **Đủ bước**: Bước 0→5 = 6 mốc, cả 6 chạy xong; `tong_ket.json` ghi `"tat_ca_buoc": "OK"`.
- **Không exception**: exit 0; 2 điểm dừng *có chủ đích đúng thiết kế*: (a) gate F3b mở cho `cause`/`fix`; (b) chặn đóng phiếu thiếu đối sách.

## 5. Cổng nền

- `compileall src tests` → OK; `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- `python -m aios_habit.cli audit` → `"status": "PASS"`, errors/warnings rỗng.
- `import aios_habit.workspace_chat_app` → `IMPORT_OK`.
- Bộ `error_cases` (đúng phạm vi vé): **105/105 đạt** trên Windows Python 3.11 (93 bài cũ gồm đủ bộ F1–F4 + 12 bài importer LSU mới; bài thứ 12 = test hồi quy digest dòng dài hơn header, thêm cùng fix `276d7d7` và chạy lại nhanh sau fix).
- Full suite nền (đúng môi trường buoc0-deploy: `AIOS_DATA_DIR=C:/tmp/aios-v14-data`, `PYTHONPATH="src;C:/tmp/e3-py311"`, `TMP=TEMP=C:/tmp`): **3.389 đạt, 2 bỏ qua, 36 lỗi, 4 error** (458,87s).
  - Đối chiếu nền TOOL-5 (`3.363/2/35/0`): **+11 đạt đúng bằng test vé** — không rớt bài nào của `error_cases` hay module mới; phần chênh lệch còn lại đến từ đợt **B1-FEAT của Muse** (`a0bb289` — 12 test: 7 đạt/1 rớt/4 error) và biến động môi trường của các bài lẻ.
  - 36 lỗi + 4 error **không thuộc phạm vi vé**: 9 `graphify_adapter`, 9 BGE worker/client, 4 đóng gói (`test_commit_d_wheel_and_packaging`), 4 `rag_v2` (eval/cli/synthesis), 9 bài lẻ workspace-chat/mom/notebook/owner-pilot/antigravity (đúng nhóm có sẵn), cộng **5 bài `test_chat_action_error_lookup`** — file này hardcode đường dẫn VM `/home/hatch/workspace/aios_data/...` (lane [VM] của vé B1-FEAT) nên không chạy được trên máy nhà.

## 6. Ràng buộc vé — đều giữ

- **Không ghi index production RAG**: không mở/ghi `library.sqlite` production hay staging nào; mọi ghi vào DB `error_cases` riêng trên ổ C.
- **Không đụng ổ D**: dữ liệu chỉ đọc từ D: rồi bỏ vào C:; mọi ghi dữ liệu (copy, DB 26,7 MB, output, log) trên `C:/tmp/lsu1-deploy/`.
- **Không merge `main`**, không force-push; chỉ push nhánh `phieu-viec/rag-fix1`.
- **Dữ liệu thật không vào Git**: chỉ code + test (fixture tổng hợp) + báo cáo; mọi số liệu dữ liệu thật nằm trong báo cáo này và trên ổ C.
- **Dữ liệu mô phỏng gắn mác `SIMULATED_*`**: rating/closure ở Bước 2 và tập labeled ở Bước 5 (fixture có sẵn của test); 1 ca đóng với `SIMULATED_*` ghi rõ trong `tong_ket.json`.

## 7. Cổng gate watcher (vòng khép kín)

Watcher tự mở OMP **1/4** lúc 03:25:44 (`launchStallCount=1`); điều kiện mở đã có ngay (mục 0) → nhận vé, cập nhật đủ 4 mốc tiến độ (03:42 / 03:54 / 03:57 / 04:02) → **không chuyển `cho-muse`, không quay no-op**.

## 8. Ghi chú và hạn chế (ngoài phạm vi vé)

- `cause`/`fix` = 0% là **kết luận thật về chất lượng dữ liệu LSU**: log vận hành không mang nguyên nhân/đối sách. Muốn đạt điều kiện Bước 0 (“≥90% đủ 5 trường”) cho list LSU cần nguồn bổ sung (biên bản điều tra, đối sách đã áp dụng…) — vé B0-MEASURE sẽ đo đầy đủ cả 2 list và ra danh sách backfill.
- Xu hướng/tái phát dùng `created_at` (= lúc nhập) nên mọi bản ghi nằm cùng tuần (2026-W40) → 1 bucket; phân tích theo ngày phát sinh thật cần vé `date-map` (đã có trong hàng chờ, phạm vi KDTPS + LSU).
- 545 file không nhập là ma trận số đo thô (`*_Depth/Profile/Spec/CamPos/Master*`, 10,5 M dòng) + ảnh/DB — không mang trạng thái lỗi nên sẽ tạo nhiễu nếu thành “ca”; giữ nguyên trên đĩa cho các vé phân tích JIG sau.
- Tài liệu LSU (ppt/pptx) mới ở mức kiểm kê + SHA; số hóa vào pipeline là việc của vé B0-DICT/B0-FORM (lane VM).
- `cam_error` thật chỉ 1 dòng (`ERR_NUM=-1306`, không khớp từ điển 4 họ mã) — số mẫu nhỏ, không đủ kết luận về mã camera.
- Importer bỏ qua dòng `FinTest` rỗng và các dòng judge trắng (không phải sự kiện) — đúng thiết kế “chỉ NG mới là ca”; con số 114.386 dòng không nhập nằm trong `tong_ket.json`.

## Kết luận

Vé `LSU-1` **hoàn tất phần thực thi**: dữ liệu LSU 888 file/1,21 GB ra ổ C có manifest + đối chiếu Drive 7/7; importer log LSU mở rộng đúng chuẩn (code `c0cbd5b` + fix `276d7d7`, 12 test, đủ bộ 105/105); **pipeline Bước 0→5 chạy end-to-end trên dữ liệu thật, exit 0**, 23.112 ca, gate F3b FAIL đúng thực tế (cause/fix 0%), 6 cảnh báo, độ chính xác 1,00 trên tập `SIMULATED_*`. Chờ Muse review + verdict.
