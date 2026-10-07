# Báo cáo kết quả chuẩn hóa thước đo chấm & Chấm lại offline (RUBRIC-NORMALIZE-PC0575)

> **THÔNG TIN VÉ:**
> - **Mã vé:** `RUBRIC-NORMALIZE-PC0575`
> - **Máy thực hiện:** `[CTY] KDTVN-PC0575` (thợ `agy` — Antigravity CLI, CPU-only).
> - **Nguồn gốc:** Báo cáo `docs/phieu-viec/ket-qua/rag-fail-analysis-pc0575.md` §5 Ưu tiên 1 (+0,360 GPA tiềm năng).
> - **Tuyên bố bắt buộc (Rào cứng):** **Điểm số tăng do sửa thước đo và đính chính bộ từ khóa lỗi của đề, KHÔNG PHẢI do hệ thống AI trả lời tốt hơn.** Đây là việc đính chính phép đo lường khách quan, toàn bộ câu trả lời được giữ nguyên từ các lần chạy đã lưu vết, không gọi lại mô hình và không gọi mạng.

---

## 1. Tóm tắt kết quả cốt lõi

| Chỉ số đo lường | Lane RAG (Trước) | Lane RAG (Sau) | Biến động RAG | Lane C-Agent (Trước) | Lane C-Agent (Sau) | Biến động C-Agent |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tổng điểm (/150)** | **46,50** | **60,50** | **+14,00 điểm** | **146,17** | **147,50** | **+1,33 điểm** |
| **Điểm trung bình (GPA)** | **0,930** | **1,210** | **+0,280 GPA** | **2,923** | **2,950** | **+0,027 GPA** |
| **Tỷ lệ ĐẠT (Điểm ≥ 2,0)** | 12/50 (24,0%) | 19/50 (38,0%) | **+7 câu (+14,0%)** | 48/50 (96,0%) | 49/50 (98,0%) | **+1 câu (+2,0%)** |
| **Tỷ lệ trích dẫn chuẩn (= 3,0)** | 3/50 (6,0%) | 6/50 (12,0%) | **+3 câu (+6,0%)** | 46/50 (92,0%) | 47/50 (94,0%) | **+1 câu (+2,0%)** |
| **Số câu thay đổi điểm** | — | **7 câu** | — | — | **1 câu** | — |

---

## 2. Chi tiết các thay đổi chuẩn hóa thước đo & Bộ đề

### 2.1. Hàm chuẩn hóa khi chấm (`normalize_text_for_eval`)
Đã triển khai trong `src/aios_habit/quality_harness.py` và áp dụng đồng nhất cho **CẢ đáp án lẫn từ khóa** trước khi so khớp chuỗi:

1. **Bỏ dấu chấm phân cách hàng nghìn:**
   - Quy tắc: Loại bỏ dấu chấm trong các số nguyên hàng nghìn (`48.384` → `48384`, `40.042` → `40042`, `3.153` → `3153`, `1.252` → `1252`, `4.399` → `4399`).
   - Bảo toàn số thập phân: Không đụng vào số có phần nguyên là 0 (`0.002`, `0.015`, `0.506`), số đo dung sai (`1.15`, `1.24`, `13.81`, `43.95`) hoặc ngày tháng (`2019.01.18`).
2. **Đổi dấu phẩy thập phân sang dấu chấm:**
   - Quy tắc: `-0,81` → `-0.81`, `1,93` → `1.93`, `2,98` → `2.98`, `49,49%` → `49.49%`, `25,04%` → `25.04%`, `43,9%` → `43.9%`.
3. **Đồng nhất đơn vị thời gian:**
   - Quy tắc: `3 giây` / `3 giay` / `3s` → `3 s`; `6 giây` / `6 giay` / `6s` → `6 s`.
4. **Đồng nhất dải nhiệt độ và đơn vị nhiệt độ:**
   - Quy tắc: `0 - 15 độ C` / `0-15°C` / `0 - 15°C` / `0 đến 15 độ C` → `0–15°C` (chuẩn hóa ký tự en-dash và đơn vị `°C`).
5. **Đồng nhất ký hiệu micro:**
   - Quy tắc: `$\mu m$` hoặc ký tự Hy Lạp `μm` (U+03BC) → ký tự Micro chuẩn `µm` (U+00B5).
6. **Đồng nhất các khái niệm diễn đạt tương đương (Semantic Phrase Normalization):**
   - Trạng thái 4M: `không phát hiện bất thường` / `thao tác không có bất thường` → `không bất thường`; `không có thay đổi 4M` → `không thay đổi`.
   - Hướng quét LSU: `drum quay` / `quay của drum` → `quay drum`; `quét chính của tia laser` → `quét ngang`.
   - Quang lượng thấu kính $f\theta$: `bị nhạt` / `trở nên nhạt` → `nhạt màu`; `vùng ngoài trung tâm` / `xung quanh` / `hai đầu hình ảnh` → `vùng biên`; cường độ ánh sáng cực đại trung tâm → `quang lượng tâm`.

### 2.2. Bảng liệt kê sửa từ khóa lỗi trong bộ đề (Tuân thủ rào cứng đúng 4 câu)

| Mã câu | Trọng tâm kiểm tra | Từ khóa cũ (TRƯỚC) | Từ khóa mới (SAU) | Lý do điều chỉnh |
|:---:|:---|:---|:---|:---|
| **`Q0630`** | Hướng quét chính và hướng quét phụ | `['DRUM.', 'DRUM.', 'LSU_2019.01.18_K.']` | `['quét ngang', 'quay drum']` | Thay từ khóa lỗi lặp có dấu chấm và tên file bằng 2 khái niệm cốt lõi định nghĩa quét chính (quét ngang) và quét phụ (quay drum). |
| **`Q0635`** | Kiểm tra Laser Power vùng biên thấu kính $f\theta$ | `['LSU_2019.01.18_K.']` | `['quang lượng tâm', 'vùng biên', 'nhạt màu']` | Thay thế việc chỉ kiểm tra duy nhất tên tệp slide bằng 3 từ khóa nội dung kỹ thuật giải thích nguyên lý quang học. |
| **`Q0674`** | Kết quả xác nhận 4M có bất thường không | `['OK']` | `['không bất thường', 'không thay đổi']` | Bổ sung từ khóa tiếng Việt vì tài liệu và câu trả lời ghi rõ 'thao tác không bất thường, không thay đổi 4M'. |
| **`Q0708`** | Chiều cao quang lộ 1.15 mm và 1.24 mm | `['1.15 mm以上', '1.24以上']` | `['1.15', '1.24']` | Chấp nhận số liệu cốt lõi của 2 ngưỡng để tránh trượt khi mô hình trả lời bằng tiếng Việt ('1.15 trở lên', '1.24 trở lên'). |

> **Cam kết tuân thủ rào cứng:** Tuyệt đối không chỉnh sửa từ khóa của bất kỳ câu nào ngoài 4 câu nêu trên.

---

## 3. Kết quả chấm lại offline Lane RAG

- **Nguồn dữ liệu:** `local_cases/lsu_quality_pc0575/rag_progress.json` (50 câu trả lời RAG đo thật từ vé `LSU-QUALITY-PC0575`).
- **Tổng điểm cũ:** **46,50 / 150,0** (GPA: **0,930**).
- **Tổng điểm mới:** **60,50 / 150,0** (GPA: **1,210**).
- **Điểm tăng thêm:** **+14,00 điểm** (tương đương **+0,280 GPA**).
- **Số câu đạt chuẩn (≥ 2,0 điểm):** Tăng từ 12 câu lên **19 câu (38,0%)**.
- **Số câu xuất sắc có trích dẫn (= 3,0 điểm):** Tăng từ 3 câu lên **6 câu (12,0%)**.

### 3.1. Danh sách 7 câu thay đổi điểm ở Lane RAG

| STT | Mã câu | Điểm cũ | Điểm mới | Mức tăng | Nguyên nhân điều chỉnh |
|:---:|:---:|:---:|:---:|:---:|:---|
| 4 | `Q0708` | 0,0/3 | **2,0/3** | **+2,0** | Khớp cả 2 ngưỡng `1.15` và `1.24` (phân biệt rủi ro C7620 và mất tín hiệu Camera). |
| 23 | `Q0635` | 0,0/3 | **2,0/3** | **+2,0** | Khớp 3/3 từ khóa nội dung (`quang lượng tâm`, `vùng biên`, `nhạt màu`). |
| 27 | `Q0674` | 1,0/3 | **3,0/3** | **+2,0** | Khớp từ khóa tiếng Việt `không bất thường`, `không thay đổi` và giữ 1,0 điểm trích dẫn. |
| 28 | `Q0677` | 1,0/3 | **3,0/3** | **+2,0** | Đồng nhất đơn vị thời gian `3 giây` = `3 s`, `6 giây` = `6 s` và giữ 1,0 điểm trích dẫn. |
| 48 | `Q0630` | 0,0/3 | **2,0/3** | **+2,0** | Khớp từ khóa khái niệm cốt lõi `quét ngang` và `quay drum`. |
| 49 | `Q0652` | 0,0/3 | **2,0/3** | **+2,0** | Bỏ dấu chấm phân cách hàng nghìn khớp `48384 vòng/phút` và `40042 vòng/phút`. |
| 50 | `Q0658` | 1,0/3 | **3,0/3** | **+2,0** | Đồng nhất dải nhiệt độ `0 - 15 độ C` = `0–15°C` và giữ 1,0 điểm trích dẫn. |

### 3.2. Đối chiếu với kỳ vọng lý thuyết ~1,290 GPA & Giải thích sai lệch

- **Kỳ vọng lý thuyết tại báo cáo trước:** **1,290 GPA** (tổng 64,50 điểm, tương ứng cả 10 câu nhóm C đều đạt điểm tối đa khi chấm tay).
- **Kết quả đo thực tế tự động bằng máy:** **1,210 GPA** (tổng 60,50 điểm, tăng +14,00 điểm).
- **Khoảng lệch so với kỳ vọng:** **4,00 điểm** (tương đương **0,080 GPA**).
- **Giải thích chi tiết nguyên nhân khoảng lệch:**
  1. **Câu `Q0709` (STT 42, Bảng quy đổi Skew sang dot — lệch 2,0 điểm):**
     - *Thực tế câu trả lời:* RAG trả lời chính xác từng màu và công thức: Cyan: -34 µm, -0,81 dot; Magenta: 81 µm, 1,93 dot; Yellow: 125 µm, 2,98 dot; Black: 0 µm, 0 dot.
     - *Lý do máy chấm 0,0 điểm:* Bộ đề cài đặt từ khóa dạng chuỗi ghép có dấu gạch chéo `['0 µm / 0 dot', '-34 µm / -0.8095 dot', ...]`. RAG trả lời theo dạng danh sách gạch đầu dòng và làm tròn 2 chữ số thập phân nên không xuất hiện chuỗi con dính liền ` / `.
     - *Xử lý theo rào cứng:* Do vé cấm tự ý sửa từ khóa ngoài danh sách 4 câu đã duyệt, câu Q0709 được giữ nguyên từ khóa của đề và ghi nhận sự lệch điểm một cách khách quan.
  2. **Câu `Q0633` (STT 33, Kiểm tra Aperture — lệch 1,5 điểm):**
     - *Thực tế câu trả lời:* Nêu chính xác APERTURE và tác dụng hạn chế nhiễu xạ, có trích dẫn `[2]`.
     - *Lý do máy chấm 1,5 điểm:* Từ khóa của đề gồm `['APERTURE.', 'APERTURE', 'LSU', 'LSU_2019.01.18_K.']`. Do dính tên tệp slide và từ khóa lỗi, máy chỉ nhận 1/4 hits từ khóa (`APERTURE`) → được 0,5 điểm chính xác + 1,0 điểm trích dẫn = 1,5 điểm.
  3. **Câu `Q0632` (STT 22, Chức năng Lens Collimate — lệch 0,5 điểm):**
     - *Thực tế câu trả lời:* Giải thích đúng chức năng biến chùm tia thành song song và tác hại lệch vị trí.
     - *Lý do máy chấm 1,5 điểm:* Từ khóa của đề gồm `['LENS', 'COLLIMATE', 'COLLIMATE', 'LSU_2019.01.18_K.']`. Model trúng 3/4 từ khóa → được 1,5 điểm chính xác (thiếu trích dẫn nguồn nên không có điểm trích dẫn).

### 3.3. Bảng điểm chi tiết 50 câu Lane RAG (Trước vs Sau chuẩn hóa)

| STT | ID | Nhóm gốc | Điểm cũ | Điểm mới | Chênh lệch | Chuẩn hoá áp dụng / Lý do biến động |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | `Q0699` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 2 | `Q0700` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 3 | `Q0703` | **B** | 0.0 | 0.0 | 0.0 | Lệch hàng bảng tính Excel trong context, giữ nguyên |
| 4 | `Q0708` | **C** | 0.0 | 2.0 | +2.0 | Chuẩn hóa từ khóa chấp nhận thêm '1.15' và '1.24' (khớp cả 2 ngưỡng quang lộ) |
| 5 | `Q0849` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 6 | `Q0850` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 7 | `Q0851` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 8 | `Q1029` | **D** | 0.5 | 0.5 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 9 | `Q1034` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 10 | `Q0620` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 11 | `Q0621` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 12 | `Q0824` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 13 | `Q0689` | **PASS** | 3.0 | 3.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 14 | `Q0704` | **A** | 0.5 | 0.5 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 15 | `Q0701` | **A** | 1.0 | 1.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 16 | `Q0718` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 17 | `Q0828` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 18 | `Q0858` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 19 | `Q0685` | **B** | 0.0 | 0.0 | 0.0 | Lệch hàng bảng tính Excel trong context, giữ nguyên |
| 20 | `Q0688` | **A** | 1.0 | 1.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 21 | `Q0695` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 22 | `Q0632` | **C** | 1.5 | 1.5 | 0.0 | Giữ nguyên (từ khóa đề dính tên tệp slide; rào cứng không sửa ngoài 4 câu cho phép) |
| 23 | `Q0635` | **C** | 0.0 | 2.0 | +2.0 | Bổ sung từ khóa nội dung 'quang lượng tâm', 'vùng biên', 'nhạt màu' (khớp 3/3) |
| 24 | `Q0636` | **PASS** | 2.5 | 2.5 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 25 | `Q1798` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 26 | `Q0671` | **A** | 0.0 | 0.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 27 | `Q0674` | **C** | 1.0 | 3.0 | +2.0 | Bổ sung từ khóa tiếng Việt 'không bất thường', 'không thay đổi' (khớp 2/2) |
| 28 | `Q0677` | **C** | 1.0 | 3.0 | +2.0 | Đồng nhất đơn vị thời gian '3 giây' = '3 s', '6 giây' = '6 s' |
| 29 | `Q0706` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 30 | `Q0707` | **A** | 0.0 | 0.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 31 | `Q0693` | **PASS** | 3.0 | 3.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 32 | `Q0696` | **A** | 1.0 | 1.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 33 | `Q0633` | **C** | 1.5 | 1.5 | 0.0 | Giữ nguyên (từ khóa đề dính tên tệp slide; rào cứng không sửa ngoài 4 câu cho phép) |
| 34 | `Q0787` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 35 | `Q1777` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 36 | `Q1827` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 37 | `Q2157` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 38 | `Q0662` | **B** | 1.0 | 1.0 | 0.0 | Lệch hàng bảng tính Excel trong context, giữ nguyên |
| 39 | `Q0665` | **B** | 1.0 | 1.0 | 0.0 | Lệch hàng bảng tính Excel trong context, giữ nguyên |
| 40 | `Q0668` | **A** | 0.0 | 0.0 | 0.0 | Trượt retrieval (không có mảnh đúng trong context), giữ nguyên 0 hoặc điểm thấp |
| 41 | `Q0705` | **PASS** | 3.0 | 3.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 42 | `Q0709` | **C** | 0.0 | 0.0 | 0.0 | Giữ nguyên (đề đòi nguyên văn chuỗi ghép có gạch chéo; model trả lời bullet -0.81 dot; rào cứng không sửa từ khóa) |
| 43 | `Q0843` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 44 | `Q0864` | **D** | 0.0 | 0.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 45 | `Q0680` | **PASS** | 2.0 | 2.0 | 0.0 | Đạt chuẩn từ trước, không bị ảnh hưởng |
| 46 | `Q0684` | **B** | 0.0 | 0.0 | 0.0 | Lệch hàng bảng tính Excel trong context, giữ nguyên |
| 47 | `Q0924` | **D** | 1.0 | 1.0 | 0.0 | Thiếu 11 tệp nguồn trong Index, model báo không đủ dữ kiện, giữ nguyên |
| 48 | `Q0630` | **C** | 0.0 | 2.0 | +2.0 | Thay từ khóa cốt lõi 'quét ngang', 'quay drum' thay vì DRUM. lặp dính chấm |
| 49 | `Q0652` | **C** | 0.0 | 2.0 | +2.0 | Bỏ dấu chấm phân cách hàng nghìn '48.384' -> '48384', '40.042' -> '40042' |
| 50 | `Q0658` | **C** | 1.0 | 3.0 | +2.0 | Đồng nhất dải nhiệt độ và đơn vị '0 - 15 độ C' = '0–15°C' |

---

## 4. Báo cáo chấm lại offline Lane C-Agent (Độc lập, không trộn lane)

- **Nguồn dữ liệu:** `local_cases/lsu_quality_pc0575/cagent_progress.json` (50 câu trả lời đo thật lane C-Agent).
- **Tổng điểm cũ:** **146,17 / 150,0** (GPA: **2,923**).
- **Tổng điểm mới:** **147,50 / 150,0** (GPA: **2,950**).
- **Điểm tăng thêm:** **+1,33 điểm** (tương đương **+0,027 GPA**).
- **Tỷ lệ ĐẠT (≥ 2,0 điểm):** Tăng từ 48/50 (96,0%) lên **49/50 (98,0%)**.
- **Tỷ lệ trích dẫn chuẩn (= 3,0 điểm):** Tăng từ 46/50 (92,0%) lên **47/50 (94,0%)**.

### 4.1. Biến động ở Lane C-Agent
- **Câu `Q0630` (STT 48):** Tăng từ **1,67/3 lên 3,00/3 tối đa (+1,33 điểm)**.
  - *Nguyên nhân:* Trước đây đề dính lỗi lặp từ khóa có dấu chấm `['DRUM.', 'DRUM.', 'LSU_2019.01.18_K.']`, C-Agent trả lời đúng hoàn toàn nhưng chỉ trúng 1/3 từ khóa (`DRUM.`) nên bị chấm 0,67 điểm chính xác + 1,0 điểm trích dẫn = 1,67 điểm.
  - *Sau khi sửa:* Từ khóa mới `['quét ngang', 'quay drum']` match 100% câu trả lời của C-Agent → Đạt 2,0 điểm chính xác + 1,0 điểm trích dẫn = **3,00 điểm tối đa**.
- **Tất cả 49 câu còn lại:** Duy trì điểm số cao ổn định, không bị giảm điểm nào.

### 4.2. Bảng điểm chi tiết 50 câu Lane C-Agent (Trước vs Sau chuẩn hóa)

| STT | ID | Điểm cũ | Điểm mới | Chênh lệch | Ghi chú |
|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | `Q0699` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 2 | `Q0700` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 3 | `Q0703` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 4 | `Q0708` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |
| 5 | `Q0849` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 6 | `Q0850` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 7 | `Q0851` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 8 | `Q1029` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 9 | `Q1034` | 1.50 | 1.50 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 10 | `Q0620` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 11 | `Q0621` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 12 | `Q0824` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 13 | `Q0689` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 14 | `Q0704` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 15 | `Q0701` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 16 | `Q0718` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 17 | `Q0828` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 18 | `Q0858` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 19 | `Q0685` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 20 | `Q0688` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 21 | `Q0695` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 22 | `Q0632` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 23 | `Q0635` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |
| 24 | `Q0636` | 2.50 | 2.50 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 25 | `Q1798` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 26 | `Q0671` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 27 | `Q0674` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |
| 28 | `Q0677` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |
| 29 | `Q0706` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 30 | `Q0707` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 31 | `Q0693` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 32 | `Q0696` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 33 | `Q0633` | 2.50 | 2.50 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 34 | `Q0787` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 35 | `Q1777` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 36 | `Q1827` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 37 | `Q2157` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 38 | `Q0662` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 39 | `Q0665` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 40 | `Q0668` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 41 | `Q0705` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 42 | `Q0709` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 43 | `Q0843` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 44 | `Q0864` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 45 | `Q0680` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 46 | `Q0684` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 47 | `Q0924` | 3.00 | 3.00 | 0.0 | Giữ nguyên điểm số xuất sắc |
| 48 | `Q0630` | 1.67 | 3.00 | +1.33 | Tăng từ 1.67 lên 3.00 tối đa: hết lỗi đề dính dấu chấm 'DRUM.' và lặp từ |
| 49 | `Q0652` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |
| 50 | `Q0658` | 3.00 | 3.00 | 0.0 | Duy trì điểm tối đa (3.0/3 hoặc 2.0/2) với thước đo mới |

---

## 5. Kết luận & Khuyến nghị kỹ thuật

1. **Hiệu quả thực tế của việc chuẩn hóa:**
   - Việc chuẩn hóa thước đo tự động đã loại bỏ thành công sự bất công trong chấm điểm cho **7/10 câu nhóm C**, nâng GPA thực tế của RAG từ **0,930 lên 1,210 (+0,280 GPA)**.
   - Đối với C-Agent, giải quyết triệt để lỗi từ khóa `Q0630`, đưa GPA lên mức xuất sắc **2,950 / 3,0 (49/50 câu ĐẠT)**.
2. **Khuyến nghị cho các vé tiếp theo (theo Roadmap ROI):**
   - **Ưu tiên 2 (Retrieval Entity Boosting):** Kéo đúng mảnh tài liệu cho 7 câu nhóm A (+0,280 GPA tiềm năng).
   - **Ưu tiên 3 (Chunking bảng Excel):** Tối ưu đọc bảng cho 5 câu nhóm B (+0,210 GPA tiềm năng).
   - **Ưu tiên 4 (Nạp bổ sung 11 tệp nguồn):** Ingest các tệp CSV đo lường và slide còn thiếu (+0,650 GPA tiềm năng).

---

## 6. Cổng kiểm thử kỹ thuật & Rào cứng

- **Python 3.11:** Đảm bảo toàn bộ lệnh chạy trong môi trường Python 3.11.
- **`compileall`:** `uv run --no-sync --group dev python -m compileall src tests` → **PASS** (100% không lỗi cú pháp).
- **Unit Tests:** `uv run --no-sync --group dev pytest tests/test_quality_harness.py -q` → **9 passed in 0.40s** (Đầy đủ ca nghìn, thập phân phẩy, đơn vị, ca sai thật không đổi điểm).
- **CLI Audit:** `uv run --no-sync --group dev python -m aios_habit.cli audit` → `status: PASS`, `errors: []`, `warnings: []`.
- **Runtime Import:** `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → Thành công.
- **Rào cứng:**
  - Không sửa `wire_qa_staging.py` (nhường OMP ở MATCHER-FIX).
  - Không sửa `rag_v2/synthesis.py`.
  - Không merge `main`.
  - Cơ sở dữ liệu Index hoàn toàn không bị chỉnh sửa.

---
*Báo cáo được lập tự động bởi Antigravity CLI (`agy`) — KDTVN-PC0575, ngày 07/10/2026.*
