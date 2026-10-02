# Vé KNOWLEDGE-ENRICH-PILOT — báo cáo máy nhà

- Ngày: 2026-10-03, 00:36–01:23 +07.
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`, không force-push.
- Lane: máy nhà, soạn bản thảo qua cầu nối Gemini Web `127.0.0.1:8585`. Không dùng Nakazasen Router, không dùng Copilot.
- Phạm vi ghi: staging `local_cases/staging_enrichment.sqlite` (không commit, thư mục đã nằm trong `.gitignore`) và artifact ở `C:/tmp/knowledge-enrich-pilot/`. Không ghi index production, không đụng ổ D dữ liệu.

## 1. Cổng gate

- Watcher tự mở lại OMP `RELAUNCH 2/4` lúc `2026-10-03T01:11:43` (`launchStallCount=2`, log `D:\Sandbox\Vong_lap_giao_viec\watcher.log`).
- Chưa đủ 4 lần. Điều kiện mở **đã tới** từ `e81ede0`: lane máy nhà, batch `KB-20261003-FCALL-01` đã xuất. Không đặt `cho-muse`, không quay no-op.

## 2. Môi trường

- Python `3.11.14` qua `uv run --no-sync --group dev`.
- `.venv` không có bản cài editable của `aios_habit` (`uv run` trần báo `ModuleNotFoundError`). Import kiểm tra bằng `PYTHONPATH=src`: schema, generator, scorer, export, importer, quality và `workspace_chat_app` đều `IMPORT_OK`. Không sửa mã sản phẩm để vá đường import.

## 3. Năm hiện tượng thật

Năm mã lấy từ bản copy chỉ đọc của `C:/tmp/b0-dict/error_cases_dict.db`, không bịa: `F000`, `F257`, `F186`, `F010`, `F040`, nhóm nằm ở `error_code_h` (CLI `--error-db` không thấy cột tên group). Mỗi mã có `case_ids` thật. Nội dung hiện tượng/giả thuyết giữ ở `C:/tmp`, không dán vào báo cáo này.

SHA-256 DB lỗi trước và sau: `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` (khớp bản copy).

## 4. Xuất batch

Batch `KB-20261003-FCALL-01`, 25 câu, file JSONL + phiếu Markdown + manifest SHA-256 ở `C:/tmp/knowledge-enrich-pilot/batch/`.

Ràng buộc chọn top-K theo scorer (D > 0, E = 1.0, ≥ 3 nhánh 4M):

| Mã | Số câu | Phân biệt giả thuyết | 4M trong top-K |
|---|---|---|---|
| F000 | 4 | D > 0 vì câu `causal_mechanism` gắn H1/H2/H3, không phải loại `discriminator` | Machine, Material, Method |
| F257 | 5 | 1 câu `discriminator` | Machine, Material, Method |
| F186 | 6 | 1 câu `discriminator` | Machine, Material, Method |
| F010 | 5 | 1 câu `discriminator` | Machine, Material, Method |
| F040 | 5 | 1 câu `discriminator` | Machine, Material, Method |

Không có nhánh Man trong top-K. Chạy lại `export_batch` trên cùng JSON hiện tượng (thư mục tạm `recheck`, không ghi đè batch đã soạn) cũng cho `constraints_met` đúng cả 5 mã — scorer tính D > 0 cả khi câu chỉ gắn ≥ 2 giả thuyết (`_score_d` trả 0.3).

## 5. Soạn bản thảo

- Cầu nối tắt (connection refused). Bật lại `scripts/antigravity_sidecar_daemon.py --mode direct`. `GET /health` = `direct_ready`.
- Probe ngoài Git: `C:/tmp/knowledge-enrich-pilot/draft_answers.py`. Công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` chỉ trong tiến trình gọi. Mỗi hiện tượng một lượt. Prompt nhắc điền đủ trường; thiếu dữ kiện thì ghi `chưa đủ bằng chứng`. Không nới schema, không sửa mã sản phẩm.
- 25/25 qua `GoldenAnswer.from_dict`. Không trường nguồn LLM. `reviewer_status` = `cho_chuyen_gia_phan_hoi`. Nhãn = `kiến thức đã được đào tạo bổ sung`. `confidence` ≤ 0.6.
- Trạng thái câu: `uncertain` 24, `answered` 1. Không nâng `uncertain` thành `answered`.
- File raw nhận lúc 01:08:57 (F000) đến 01:16:30 (F040). `answered_at` trong form để trống.

## 6. Nhập staging

Lệnh: `python -m aios_habit.golden_answer_importer` với `--answers` JSONL, `--manifest` batch, `--staging local_cases/staging_enrichment.sqlite`, và `--prod-db` trỏ index production cùng DB lỗi.

Kết quả: nhập 25, trùng 0, claim 1 (chỉ câu `answered`), xung đột 0. Đọc lại staging (chế độ chỉ đọc):

- `staging_answers` = 25, SHA phân biệt = 25
- nhãn duy nhất: `kiến thức đã được đào tạo bổ sung`
- trạng thái duy nhất: `cho_chuyen_gia_phan_hoi`
- `expert_reviews` = 0
- payload không có trường nguồn LLM

## 7. Không đụng kho chính / luồng trả lời chính

| File | SHA trước | SHA sau | Khớp |
|---|---|---|---|
| `library.sqlite` production | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA | có |
| `error_cases_dict.db` | `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` | cùng SHA | có |

Ba DB hội thoại (`workspace_chat.sqlite` production, bản trong `bge_m3_hybrid`, `local_cases/workspace_cases.sqlite`) có mtime cũ hơn phiên này (01/10, 02/10, 13/09). Tìm chỉ đọc các chuỗi `KB-20261003-FCALL-01`, nhãn làm giàu, `STAGING-GQ`, `staging_enrichment`: 0 dòng. Mã sản phẩm chỉ nhắc `staging_enrichment` trong importer. Không bản thảo nào vào luồng trả lời chính.

## 8. Bộ đo trước/sau

Chạy `run_before_after` trên cùng 5 câu chuẩn. Adapter trước: nguồn ca lỗi có mặt, điểm phủ 0.35, lý do `insufficient_evidence` (gap mức medium, không bịa `missing_source`). Adapter sau: chỉ trong bộ nhớ, gắn đoạn staging mang `STAGING-GQ` / `golden_new`. Không ghi index.

| Mốc | Số | Ngưỡng thiết kế | Kết luận hàm đo |
|---|---|---|---|
| M1 gap high | trước 0, sau 0, giảm 0% | ≥ 60% | không đạt — công thức trả 0 khi trước không có gap high |
| M2 chunk mới trong top-5 | 5/5 | ≥ 4/5 | đạt trên adapter bộ nhớ |
| M3 độ đầy form | 1.000; bằng chứng đo được 1.000; nhân quả đầy đủ 1.000 trên 1 câu `answered` | ≥ 80% | đạt theo hàm |
| M4 phân biệt giả thuyết | 4/7 = 57,1% | ≥ 70% | không đạt |
| Thời gian trả lời | `answered_at` trống | không có ngưỡng đạt/rớt | khoảng file raw 01:08:57–01:16:30 +07 |

`overall_pass()` = false.

Đọc thêm, không đổi verdict của hàm: 25/25 gap trong file câu hỏi là `priority=high`, `gap_type=missing_condition`. Không ghi các gap này ngược vào kho, nên số gap high trên production không giảm. M2 không phải retrieval trên `library.sqlite` — SHA index không đổi nên chunk mới không có trong index. M4 hụt vì F000 có 3 cặp giả thuyết nhưng không có câu loại `discriminator` (scorer vẫn tính D > 0).

## 9. Chờ duyệt

Phần máy nhà đã chạy hết các bước vé: sinh/chọn câu trên 5 mã F CALL thật, xuất batch, soạn bản thảo qua Gemini Web, nhập staging, đo SHA, chạy bộ đo. Không gắn `chuyen_gia_da_phan_hoi`. Không merge `main`.

Ngưỡng M1 và M4 của bộ đo **chưa đạt**. Không tự đánh ĐẠT toàn vé. Muse review file này.
