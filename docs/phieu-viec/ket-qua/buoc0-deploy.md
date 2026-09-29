# Vé `buoc0-deploy` — Deploy Bước 0–5 (error_cases) lên máy nhà: nghiệm thu

- Trạng thái: **ĐẠT** — đạt deadline 30/09 23:59 (hoàn tất ~02:47 sáng 30/09, trước ~21 tiếng).
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (`.venv` của repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `9f08cf7` (nhận vé) → `4a50dfc` (mốc test) → `54ed330` (mốc pipeline). Không đụng `main`, không force-push.
- Dữ liệu thật: `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/` — gói thật tải từ Drive (Vé V1.4 đã đối chiếu 4 SHA-256).
- Phạm vi ghi: DB + output + log đặt trên ổ C (`C:/tmp/buoc0-deploy/`); repo chỉ nhận báo cáo này + `docs/phieu-viec/mailbox/trang-thai.md`. Không ghi index production RAG.

## 1. Việc 1 — Pull branch mới nhất

02:30 ngày 30/09: `git pull origin phieu-viec/rag-fix1` → HEAD `4ada8d0` (đã gồm E3 + E4 xong). Không tạo merge.

## 2. Việc 2 — 79 test trên Windows Python 3.11 → PASS

Môi trường: repo `.venv` Python `3.11.14` (chạy qua `uv run --no-sync --group dev`); `PYTHONPATH=C:/tmp/e3-py311` để có `xlrd 2.0.2`; `AIOS_DATA_DIR=C:/tmp/aios-v14-data` (dữ liệu thật); `TMP=TEMP=C:/tmp`.

```
uv run --no-sync --group dev python -m pytest \
  tests/test_error_cases_f1.py tests/test_error_cases_f2.py tests/test_error_cases_f3.py \
  tests/test_feedback_loop.py tests/test_investigation_tree.py tests/test_trend_analysis.py \
  tests/test_auto_classifier.py -q
```

Kết quả: **79 passed, 0 failed** (4,05 giây) — đúng con số 79 của vé (7 tệp).

Mở rộng, chạy đủ **cả bộ error_cases 9 tệp = 93 test** (thêm `test_error_cases_f4.py` 11 test cần 4 bảng mã lỗi thật + `test_line_investigation.py` 3 test):

| Bộ | Số test | Kết quả |
|---|---:|---|
| 7 tệp đúng như vé ghi | 79 | **79 passed / 0 failed** (4,05s) |
| Đủ 9 tệp error_cases | 93 | **93 passed / 0 failed** (4,66s) |

Không test nào bị xóa/sửa để lấy PASS; không sửa mã nguồn hay test trong vé này.

## 3. Việc 3 — Pipeline Bước 0–5 với dữ liệu thật → chạy xong, 0 lỗi

Runner: `C:/tmp/buoc0-deploy/run_pipeline.py` (script tạm trên ổ C, không commit);
DB riêng: `C:/tmp/buoc0-deploy/error_cases_deploy.db`; log đầy đủ: `C:/tmp/buoc0-deploy/chay.log`; tổng kết JSON: `C:/tmp/buoc0-deploy/tong_ket.json`.

| Mốc | Việc đã chạy | Kết quả thật |
|---|---|---|
| Bước 0 (nền) | schema + nạp 4 bảng mã lỗi thật vào từ điển | C_CALL 226 + F_SYSTEM 127 + SCT_ADJ 37 + JAM 3.430 = **3.820 mục**; tra thử C0030 → "Bất thường hệ thống bản mạch FAX" |
| Bước 1 (nhập + gate F3b) | `import_history` file thật `Loi KDTPS.xlsx` (sheet "History KDTPS") | 15.737 dòng đọc → **15.724 nhập** (13 dòng skip thiếu A/B hoặc D/E), 104s; DB **15.707 ca** (17 dòng trùng khoá `no_dvd+machine+line` được gộp theo thiết kế); gate **F3b FAIL đúng thiết kế**: chỉ trường lõi `fix` 56,7% < 90% (khớp dự báo 56,8% từ 27/09); các trường lõi khác 99,9–100% |
| Bước 2 (feedback loop) | 3 ca thật (2023/1, 2023/2, 2023/3): gọi gợi ý → đánh giá → đóng phiếu | coverage 1,0 (3/3); đóng phiếu ghi ngược nguyên nhân/đối sách thật vào `investigation`; **chặn đúng** khi thiếu đối sách: "Không đóng được phiếu: thiếu đối sách thật (actual_countermeasure)." |
| Bước 3 (cây điều tra) | hiện tượng thật lấy từ cột mô tả khuyết điểm của History + mã thật C0030 | 4 nhánh 4M + 16 checklist + 5 cấp Why-Why → `out/buoc3_cay_dieu_tra.md` |
| Bước 4 (xu hướng) | `run_periodic_report` trên 15.707 bản ghi, 3 chiều (Model/Line/Công đoạn) | Bảng tỉ lệ phát sinh + 1 cảnh báo vượt ngưỡng (chiều Công đoạn "(không rõ)" 100% > 20%) → `out/buoc4_bao_cao_xu_huong.md` |
| Bước 5 (phân loại + tái phát) | phân loại C0030 + so lịch sử + dò tái phát mã thật + đo độ chính xác | C0030 → nhóm `linh_kien`, công đoạn "Kiểm tra", bộ phận "Điện", conf 0,75, 5 match lịch sử; tái phát mã `ERROR` (3.568 lần trong lịch sử thật) → cảnh báo kèm đối sách lấy từ lịch sử; accuracy tập `SIMULATED_*` (12 ca dựa trên domain thật): 1,00 / 1,00 / 1,00 |

Runtime toàn pipeline: **112 giây, exit code 0**.

## 4. Việc 4 — Kiểm tra output: đúng format, đủ bước, không lỗi

- **Đúng format**: runner có assert từng file output — Bước 1 (bảng field + dòng gate F3b), Bước 3 (đủ mục "1. Cây điều tra 4M" + "2. Chuỗi Why-Why"), Bước 4 (đủ 3 phần + "Bảng tỉ lệ phát sinh" + "Cảnh báo") — tất cả đạt.
- **Đủ bước**: chuỗi Bước 0→5 = 6 mốc (nền 0 + nghiệp vụ 1–5); cả 6 chạy xong, không mốc nào bị bỏ; tổng kết `"tat_ca_buoc": "OK"`.
- **Không lỗi**: không exception nào; 2 điểm dừng *có chủ đích đúng thiết kế*: (a) gate F3b mở vé backfill `fix`; (b) chặn đóng phiếu thiếu đối sách.

File output: `C:/tmp/buoc0-deploy/out/buoc1_gate_f3b.md`, `buoc3_cay_dieu_tra.md`, `buoc4_bao_cao_xu_huong.md`.

## 5. Cổng nền

- `uv run --no-sync --group dev python -m compileall -q src/aios_habit/error_cases` → OK.
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"`, `errors`/`warnings` rỗng.
- `import aios_habit.error_cases` → OK (68 symbol công khai).
- `import aios_habit.workspace_chat_app` → `IMPORT_OK`.
- Full suite nền `pytest -q` (kèm `AIOS_DATA_DIR` dữ liệu thật): **3.276 đạt, 2 bỏ qua, 37 lỗi, 0 error** (501,85s). So nền E4 (`3.265 đạt/3 bỏ qua/37 lỗi/10 error`): +11 đạt (đúng nhóm F4 nay có dữ liệu thật), hết 10 error thiếu dữ liệu, **37 lỗi không đổi** và không bài nào thuộc error_cases (graphify_adapter ×9, bge worker/client ×9, wheel-packaging ×4, eval harness ×2, owner workflow ×2, các bài lẻ workspace-chat/mom/notebook — đúng nhóm có sẵn đã liệt kê ở E3/E4).

## 6. Ràng buộc vé — đều giữ

- **Không merge `main`**: không commit nào trên `main`; chỉ push nhánh `phieu-viec/rag-fix1`.
- **Không đụng index production RAG**: DB error_cases là file SQLite riêng trên ổ C; không mở/ghi index.
- **Không đụng ổ D (dữ liệu)**: mọi ghi dữ liệu (DB 49 MB, output, log) trên `C:/tmp/buoc0-deploy/`; repo chỉ thêm báo cáo + cập nhật `trang-thai.md`.
- **Dữ liệu mô phỏng gắn mác `SIMULATED_*`**: rating/`closed_by`/note ở Bước 2; tập labeled accuracy ở Bước 5 (fixture có sẵn trong repo từ `f8eb879`, docstring ghi rõ dựa trên domain thật, không phải dữ liệu công ty). Không bịa dữ liệu.
- **Dữ liệu thật không vào Git**: chỉ ghi đường dẫn + số liệu vào báo cáo.

## 7. Cổng gate watcher

Watcher tự mở OMP **1/4** lúc 02:28:49 (`launchStallCount=1`, sig vé `buoc0-deploy`); điều kiện mở đã có ngay (dữ liệu thật còn trên máy + Python 3.11 sẵn sàng) → nhận vé ngay, cập nhật 3 mốc tiến độ (02:39 / 02:42 / 02:47) → **không chuyển `cho-muse`, không quay no-op**.

## 8. Ghi chú và hạn chế (ngoài phạm vi vé)

- Gate **F3b đang mở** với trường `fix` (56,7%): cần vé F3b backfill riêng — đúng như Muse dự báo từ 27/09; không phải lỗi của lượt deploy này.
- Xu hướng/tái phát dùng `created_at` (= lúc nhập) nên mọi bản ghi nằm cùng tuần/cửa sổ 12h → 1 bucket và chiều "Công đoạn" chưa có nguồn trong history_29 nên gom "(không rõ)". Hành vi module đúng thiết kế; muốn phân tích theo ngày phát sinh thật cần vé sau (map cột ngày X/Y của history_29).
- 13 dòng skip và 17 dòng gộp trùng (15.724 → 15.707) thuộc hành vi importer đã kiểm bằng test; không phải lỗi.

## Kết luận

Vé `buoc0-deploy` **ĐẠT**: 79/79 test (đủ bộ 93/93) pass trên Windows Python 3.11; pipeline Bước 0–5 chạy end-to-end trên dữ liệu thật với output đúng format, đủ bước, không lỗi; đạt deadline 30/09 23:59.
