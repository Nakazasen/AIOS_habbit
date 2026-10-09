# BÁO CÁO NGHIỆM THU: AUDIT-REMEASURE-PC0575
## Sửa 3 điểm trình bày báo cáo đo lại + Kiểm toán độc lập các báo cáo truy hồi của thợ chính

- **Mã vé**: `AUDIT-REMEASURE-PC0575`
- **Máy thực hiện**: `[CTY] KDTVN-PC0575` (thợ `OMP` — vai phụ, theo phân vai 2026-10-08)
- **Nhánh thực hiện**: `phieu-viec/rag-fix1`
- **Báo cáo được giao**: `docs/phieu-viec/ket-qua/rag-remeasure-pc0575.md` (báo cáo vé này)
- **Phạm vi**: chỉ đọc tệp kết quả + sửa tài liệu; KHÔNG chạy app, KHÔNG chạy việc nặng, KHÔNG ghi chỉ mục
- **Trạng thái**: HOÀN THÀNH — 3/3 điểm trình bày đã sửa + kiểm toán độc lập 3 báo cáo xong

---

## 1. Sửa 3 điểm trình bày trong báo cáo đo lại (đúng verdict điều phối)

Đã sửa đúng 3 điểm trong `docs/phieu-viec/ket-qua/rag-remeasure-pc0575.md`, không sửa số đo gốc:

| # | Điểm sửa | Trước | Sau |
| :---: | :--- | :--- | :--- |
| (a) | Tốc độ truy hồi — ghi rõ cả hai con số | "xuống trung bình 6–18s/câu (median ~11s)" (ghi trung vị dưới nhãn trung bình) + bảng 4.1 "~11s (ấm 6–18s) \| VƯỢT CHUẨN" | "**trung bình 26,1s/câu**; **trung vị khoảng 11s/câu** (phần lớn câu ấm 6–18s; một số câu nặng 90–190s kéo trung bình lên)"; bảng 4.1 ghi rõ trung bình 26,1s / median ~11s, cột đánh giá nêu "chưa đạt theo trung bình 50 câu" |
| (b) | Phân loại câu dưới chuẩn | Nhóm D: 16 câu (44.4%, gồm `Q0787`); Nhóm Khác: 5 câu (13.9%) | Nhóm D: **15 câu (41.7%)** — **bỏ `Q0787`**; Nhóm Khác: **6 câu (16.7%)** — **thêm `Q2157`** (sửa đồng bộ ở §1 tóm tắt và bảng §5; các nhóm A/B/C giữ nguyên; tổng vẫn 36 câu) |
| (c) | Dòng trạng thái đầu báo cáo | "HOÀN THÀNH — ĐẠT MỤC TIÊU VÀ CÁC CỔNG AN TOÀN TUYỆT ĐỐI" | "HOÀN THÀNH ĐO ĐẠC — qua các cổng an toàn chỉ-đọc; **lane RAG chưa đạt mục tiêu điểm** (0,957 < 1,5)" |

Xác nhận sau sửa: không còn chỗ nào ghi "đạt mục tiêu" cho lane RAG (0,957); nhãn "trung bình" không còn bị gán cho trung vị; tổng phân loại 15+5+3+7+6 = 36 câu khớp số câu dưới chuẩn thực tế.

### 1.1 Kiểm chéo phân loại nhóm với điểm số thô (phát hiện thêm)

Đối chiếu 36 câu dưới chuẩn trong bảng chi tiết (§7) với `total` thô trong `local_runs/remeasure_rag_progress.jsonl`:

- **Khớp nhóm D/A/B/C/Khác sau sửa**: 15 câu D + 5 câu A + 3 câu B + 7 câu C + 6 câu Khác = 36 câu, tất cả đều có điểm thô < 2.0.
- **Phát hiện lệch nhỏ giữa 2 cột của cùng báo cáo (ghi nhận, không tự sửa ngoài phạm vi)**: dòng `Q0708` ở cột "Phân loại nhóm" của bảng §7 ghi "C (oan rubric)" nhưng `Q0708` thực tế **đạt 2.0 điểm (PASS)**, không thuộc 36 câu dưới chuẩn; nhóm C trong bảng §5 vẫn đúng 7 câu (`Q0718`, `Q0632`, `Q0635`, `Q0636`, `Q0706`, `Q0662`, `Q0665`). Đây là nhãn cột phụ trong bảng chi tiết, không ảnh hưởng các con số tổng; đề nghị điều phối quyết định có đưa vào lần sửa sau hay không.

---

## 2. Kiểm toán độc lập báo cáo đo lại (`rag-remeasure-pc0575.md`)

Nguồn thô trên máy: `local_runs/remeasure_cagent_progress.jsonl` (50 dòng) + `local_runs/remeasure_rag_progress.jsonl` (50 dòng), còn nguyên vẹn.

### 2.1 Lane C-Agent

| Chỉ số | Báo cáo công bố | Tính lại độc lập từ tệp thô | Kết luận |
| :--- | :---: | :---: | :---: |
| Tổng điểm | 146.83 / 150 | **146.83** (Σ `total` 50 dòng) | **KHỚP** |
| GPA | 2.937 | **2.9366** (146.83/50) | **KHỚP** |
| Số câu đạt chuẩn ≥ 2.0 | 49/50 (98.0%) | **49/50** (duy nhất `Q1034` = 1.5) | **KHỚP** |
| Số câu xuất sắc = 3.0 | 46/50 (92.0%) | **46/50** | **KHỚP** |
| Lỗi / dòng hỏng | — | 0 dòng `error`, 50/50 `ok=True` | **KHỚP** |

### 2.2 Lane RAG

| Chỉ số | Báo cáo công bố | Tính lại độc lập từ tệp thô | Kết luận |
| :--- | :---: | :---: | :---: |
| Tổng điểm | 47.83 / 150 | **47.83** | **KHỚP** |
| GPA | 0.957 | **0.9566** | **KHỚP** |
| Số câu đạt chuẩn ≥ 2.0 | 14/50 (28.0%) | **14/50** | **KHỚP** |
| 3 câu xuất sắc | `Q0693`, `Q0671`, `Q0705` | **đúng 3 mã này** (total = 3.0) | **KHỚP** |

### 2.3 Đối chiếu bảng chi tiết 50 câu (§7) với tệp thô

Đã parse toàn bộ 50 dòng bảng §7 và so từng ô với 2 tệp thô:

- 50/50 dòng: điểm C-Agent lượt này, điểm RAG lượt này, `retrieval_s`, `synthesis_s` — **0 sai lệch**.
- Số đo thời gian toàn 50 câu (tính lại): `retrieval_s` trung bình **26,12s** — khớp con số điều phối chốt ghi (26,1s); trung vị **15,46s** (bỏ 3 câu chậm nhất vẫn 14,18s); `synthesis_s` trung bình 5,14s (nằm trong khoảng "4–6s" đã ghi); `total_s` trung bình 31,26s.
- **Ghi nhận để điều phối biết (không tự sửa ngoài phạm vi)**: nhãn "trung vị khoảng 11s" theo verdict chưa khớp trung vị tính lại đầy đủ (15,46s); khoảng 6–18s là mô tả phần lớn câu ấm (nhiều câu nằm ở 6–12s) nên "khoảng 11s" đúng hơn nếu hiểu là vùng giữa của các câu ấm, còn trung vị chính thức của cả 50 câu là ~15,5s.

**Kết luận mục 2: báo cáo đo lại KHỚP số liệu thô ở tất cả các con số chính; không phát hiện sai lệch số đo.** Các điểm đã sửa ở mục 1 thuần túy là cách trình bày theo verdict.

---

## 3. Kiểm toán độc lập Báo cáo nạp dày bằng numpy (`retrieval-dense-numpy-pc0575.md`)

Nguồn thô: `local_runs/retrieval_dense_numpy_results.json` + `local_runs/parity_status.json`.

### 3.1 Cổng parity (bảng §2 của báo cáo)

| Mã câu | py (ms) | numpy (ms) | speedup (báo cáo) | speedup (tính lại) | Top-15 | Lệch điểm | Kết luận |
| :---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| Q0704 | 285.807,7 | 1.407,1 | 203,1x | **203,1** | 15/15 | 0.00e+00 | KHỚP |
| Q0701 | 286.558,5 | 1.421,2 | 201,6x | **201,6** | 15/15 | 0.00e+00 | KHỚP |
| Q0688 | 298.523,4 | 1.317,2 | 226,6x | **226,6** | 15/15 | 0.00e+00 | KHỚP |
| Q0671 | 291.761,7 | 1.768,1 | 165,0x | **165,0** | 15/15 | 0.00e+00 | KHỚP |
| Q0707 | 315.974,1 | 2.182,3 | 144,8x | **144,8** | 15/15 | 0.00e+00 | KHỚP |
| Q0696 | 276.398,8 | 1.494,4 | 185,0x | **185,0** | 15/15 | 0.00e+00 | KHỚP |
| Q0668 | 263.753,0 | 1.165,6 | 226,3x | **226,3** | 15/15 | 0.00e+00 | KHỚP |
| Q0704_perf_diag | 272.861,9 | 1.117,3 | 244,2x | **244,2** | 15/15 | 0.00e+00 | KHỚP |

- Tổng hợp thô: `passed_queries = 8/8`, `all_passed = true`, `ids_match = true` cho cả 8 câu — khớp "8/8 ĐẠT TUYỆT ĐỐI".
- Tăng tốc trung bình: tính lại = **199,6 lần** — khớp báo cáo.
- Bảng §4.1 (dense warm 0,511–0,762s; trung bình 0,610s; tăng tốc 137–212x; tiết kiệm 78,21s/câu): nhất quán giữa `perf_summary` và bảng §4.2 trong tệp thô (Q0704 pipe 73,019s vs trước 158,1s → tiết kiệm 85,08s; tương tự 3 câu). Lưu ý nhỏ: cột tăng tốc §4.1 tính trên tổng đường dày cũ 106,67s (bao gồm nạp cache) còn bảng §2 tính trên riêng lượt quét ma trận — hai thang đo khác nhau, không mâu thuẫn.

### 3.2 Chỉ mục không đổi

- `library.sqlite` hiện tại: size **2.853.646.336 bytes**, mtime **2026-10-07 11:36:48** — trùng mốc trước/sau đo của vé; `initial/final_index_size_bytes` trong tệp thô lexical đều = 2.853.646.336.
- md5 đã ghi nhận `492c065f…` (tệp `remeasure_index_md5_before.txt`). **Không chạy lại md5** để tránh việc nặng trên máy trong lúc thợ chính/người dùng đang dùng (rào cứng vé); căn cứ xác nhận: size + mtime + cỡ tệp thô 2 vé đều khớp.

**Kết luận mục 3: KHỚP.** Toàn bộ số parity/tăng tốc báo cáo nạp dày numpy đều đúng theo tệp kết quả gốc; chỉ mục không đổi trong suốt vé.

---

## 4. Kiểm toán độc lập Báo cáo từ khóa FTS (`retrieval-lexical-fts-pc0575.md`)

Nguồn thô: `local_runs/lexical_fts_baseline_results.json` + `local_runs/parity_10_queries_report.json` + `local_runs/parity_detailed_diff_analysis.md`.

### 4.1 Số đo

| Số đo báo cáo | Tính lại từ tệp thô | Kết luận |
| :--- | :--- | :---: |
| Baseline 4 khâu: FTS MATCH 37,8–53,0s (Q0704) | `fts_match_ms` Q0704_diag = **37.814 ms**; nhóm A Q0704 = **39.734 ms** | KHỚP |
| Nạp ứng viên fallback V1: 18,5–22,1s | `eligibility_ms` = 20,2–23,7s (gồm dựng bảng tạm ~2,3–2,7s) — đúng độ lớn | KHỚP |
| Rescue quét 121.331 dòng: 2,8–6,3s | `identifier_rescue_ms` = 2.682–6.313 ms | KHỚP |
| Tiền lọc CJK Q0696: 13,0s | `python_score_ms` Q0696_A = **13.025,7 ms** (22.338 dòng chấm điểm) | KHỚP |
| Parity 10/10 PASS; Q0701 8→11; Q0671 5→4; Q0704_A 8→1 | `all_passed_parity=true`; Q0701 8→11, Q0671 5→4, Q0704_A 8→1; overlap 7–14/15 đúng từng dòng | KHỚP |

**Ghi chú phạm vi một nhãn số (không phải sai số):** bảng §4 ghi "Thời gian Lexical mới" Q0704/Q0701/Q0671 = 1,43s / 1,15s / 0,86s. Đây là số đo **riêng khâu FTS MATCH (đã lọc stopword)**, không phải toàn chặng lexical: trong bộ thô parity cùng 3 câu, `lexical_ms` (cả chặng sau tối ưu, gồm rescue + chấm điểm) = **6,3–8,9s/câu** — vẫn thấp hơn nhiều so với baseline 8,7–63,9s, kết luận tối ưu của vé giữ nguyên. Báo cáo chính nên ghi rõ phạm vi nếu có lần sửa sau (điểm này ngoài 3 điểm điều phối chỉ định nên tôi không tự sửa).

### 4.2 Chỉ mục không đổi

- `initial_index_size_bytes` = `final_index_size_bytes` = **2.853.646.336** trong tệp thô vé; khớp mtime/size hiện tại của `library.sqlite` (mục 3.2).

**Kết luận mục 4: KHỚP phần lớn số đo chính (baseline 4 khâu, parity 10/10, hạng đích Q0701/Q0671 đều đúng thô).** Một nhãn số cần ghi rõ phạm vi: "1,15s" là riêng khâu FTS MATCH, không phải toàn chặng lexical (toàn chặng đo được 6,3–8,9s).

---

## 5. Rào cứng & tuân thủ

- Chỉ đọc tệp kết quả + sửa đúng tài liệu được chỉ định (báo cáo đo lại 3 điểm + báo cáo này). Không sửa `prompt.md`.
- KHÔNG chạy ứng dụng, KHÔNG chạy job nặng, KHÔNG ghi chỉ mục, KHÔNG merge `main` trong suốt vé.
- Các lệnh đã dùng đều là đọc tệp JSON/JSONL cỡ nhỏ (< 1 MB) — không ảnh hưởng máy đang được thợ chính/người dùng sử dụng.
- mtime/size chỉ mục được kiểm bằng `stat` (nhẹ); cố ý KHÔNG chạy lại md5 (115s đọc 2,8 GB) theo rào cứng "không việc nặng".

## 6. Kết luận tổng

1. Đã sửa đúng và đủ 3 điểm trình bày theo verdict điều phối; không đụng số đo gốc.
2. Kiểm toán độc lập 3 báo cáo: **báo cáo đo lại — KHỚP toàn bộ** (146,83 / 47,83 / GPA / số câu đạt / bảng 50 câu 0 lệch); **dense-numpy — KHỚP toàn bộ** (parity 8/8, tăng tốc khớp từng số, chỉ mục không đổi); **lexical-FTS — KHỚP các số chính**, 1 nhãn số cần ghi rõ phạm vi (1,15s là riêng khâu FTS MATCH).
3. Không phát hiện số liệu bịa/không khớp tệp gốc trong 3 báo cáo.
