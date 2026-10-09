# Báo cáo kết quả vé SYNTH-EVIDENCE-GATE-AUDIT-HOME: Rà ngưỡng độ phủ từ khoá của Cổng kiểm chứng bằng chứng cho câu chẩn đoán ngắn

- **Mã vé:** `SYNTH-EVIDENCE-GATE-AUDIT-HOME`
- **Thợ thực hiện:** agy (máy nhà `h410asrock`)
- **Mục tiêu:**
  1. Đo phân bố thực tế từ các tệp dữ kiện đo đã có: với mọi câu từng bị Cổng kiểm chứng bằng chứng (Evidence Gate) chặn, trích độ phủ từ khoá đã tính, độ dài câu hỏi và bằng chứng truy hồi được đi kèm. Phân nhóm: câu chẩn đoán ngắn (< 50 ký tự) và các nhóm còn lại.
  2. Chấm lại bằng tay có căn cứ một mẫu đại diện trong nhóm bị chặn: đọc từng mẩu bằng chứng truy hồi được và kết luận bằng chứng đó đủ hay không đủ để trả lời có trích dẫn. Đây là căn cứ thực nghiệm duy nhất để bàn về ngưỡng.
  3. Mô phỏng trên dữ kiện có sẵn: nếu hạ ngưỡng độ phủ cho nhóm câu chẩn đoán ngắn xuống các mức ứng viên thì có bao nhiêu câu được thả, và trong số đó bao nhiêu câu thuộc nhóm "bằng chứng đủ", bao nhiêu câu thuộc nhóm "bằng chứng không đủ". Chỉ đề xuất mức ngưỡng khi mô phỏng cho thấy không thả lọt câu thiếu bằng chứng.
  4. Áp dụng điều khoản Bước 4 của vé: Nếu và chỉ nếu Bước 3 cho kết quả sạch mới áp thay đổi ngưỡng. Nếu Bước 3 không sạch: không áp gì cả, báo cáo kết luận giữ nguyên ngưỡng kèm dữ kiện.
- **Tệp dữ kiện thô nộp kèm:**
  - `docs/phieu-viec/ket-qua/ket-qua-synth-evidence-gate-audit-home.json` (149.473 bytes đo trên bản nộp kho git blob size; 152.097 bytes trên đĩa Windows CRLF)
- **Môi trường & Rào cứng:**
  - Python 3.11.14 (`cpython-3.11-windows-x86_64-none`), môi trường repo `AIOS_habbit` nhánh `phieu-viec/rag-fix1`.
  - Cổng kiểm chứng là cơ chế an toàn đóng kín (fail-closed): mọi thay đổi phải có dữ kiện mô phỏng chống lưng và khả năng hoàn lui.
  - Không ghi đè chỉ mục production `library.sqlite` (bảo toàn nguyên vẹn 2.942.201.856 bytes).
  - Không đổi bộ đề và thang chấm rubric. Không merge `main`.
- **Trạng thái:** `HOÀN THÀNH - NỘP XONG-CHO-DUYET`.

---

## 1. Tóm tắt sự thật kỹ thuật & Quyết định kiến trúc an toàn

### 1.1. Kết luận tiên quyết của Bước 3: BƯỚC 3 KHÔNG SẠCH (DIRTY SIMULATION)

Sau khi đối soát độc lập và đọc bằng tay từng mẩu bằng chứng truy hồi của toàn bộ các câu bị cổng chặn:
1. **100% câu chẩn đoán ngắn (< 50 ký tự) bị chặn đều là CHẶN ĐÚNG (True Negatives):**
   - Trong số 8 câu bị chặn ở lượt đo hiện hành, có **7 câu thuộc nhóm chẩn đoán ngắn** (`Q0620`, `Q0668`, `Q0824`, `Q0843`, `Q0849`, `Q0850`, `Q1034`).
   - Kết quả đọc bằng tay toàn bộ các mẩu bằng chứng truy hồi được của 7 câu này xác nhận: **0 / 7 câu có đủ bằng chứng** để trả lời câu hỏi và trích dẫn số liệu theo yêu cầu của đề bài. Toàn bộ 7 câu đều thiếu hụt trầm trọng dữ liệu cốt lõi (thiếu bảng tỷ lệ NG, thiếu nominal giới hạn, nhầm lẫn khái niệm cơ khí thay vì dòng điện, thiếu sheet tổng hợp record...).
   - Cổng Evidence Gate đã hoạt động **hoàn toàn chính xác theo nguyên tắc Fail-Closed của Hiến pháp AIOS**: thà từ chối không gọi LLM còn hơn gửi bằng chứng rác ra mô hình ngoài gây ảo giác (hallucination).
2. **Mọi mức hạ ngưỡng mô phỏng đều THẢ LỌT 100% CÂU THIẾU BẰNG CHỨNG:**
   - Khi mô phỏng hạ ngưỡng xuống các mức ứng viên `0.50`, `0.35`, `0.20`, `0.10`: toàn bộ các câu được thả ra đều thuộc nhóm "bằng chứng không đủ" (tỷ lệ thả lọt sai đạt 100%).
   - Không tồn tại bất kỳ mức ngưỡng nào có thể thả được câu đúng mà không làm lọt câu sai trong nhóm chẩn đoán ngắn.
3. **Thực thi Bước 4 theo đúng hợp đồng của vé:**
   - Hợp đồng quy định rõ: *"Nếu bước 3 không sạch: không áp gì cả, báo cáo kết luận giữ nguyên ngưỡng kèm dữ kiện."*
   - Do đó, thợ **GIỮ NGUYÊN NGƯỠNG AN TOÀN `min_final_evidence_term_coverage = 0.60`**, không áp bất kỳ thay đổi nào vào mã nguồn, bảo vệ nguyên vẹn cơ chế an toàn đóng kín của hệ thống.

### 1.2. Phát hiện kiến trúc quan trọng: Cơ chế cứu viện hai kênh (Dual-Channel Resilience)

Qua phân tích phân bố toàn bộ 50 câu RAG LSU:
- Có tới **29 / 50 câu** có độ phủ từ khoá lexical dưới ngưỡng 0.60 (`final_evidence_term_coverage < 0.60`).
- Tuy nhiên, chỉ có đúng **8 câu bị chặn (Abstain)**, trong khi **21 câu vẫn được thông cổng** an toàn sang chế độ `answer_with_limits` và đạt điểm rất cao (như `Q0699` đạt 2.0đ, `Q0700` đạt 1.0đ, `Q0703` đạt 3.0đ, `Q0708` đạt 1.0đ, `Q0688` đạt 1.0đ, `Q0709` đạt 1.0đ...).
- **Cơ chế:** Nhờ kiến trúc hai kênh trong [`src/aios_habit/rag_v2/evidence.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/evidence.py#L805-L815): khi độ phủ từ khoá không đạt nhưng kênh ngữ nghĩa vector đậm đặc (`semantic_dense`) từ mô hình BGE-M3 xác nhận có hỗ trợ ngữ nghĩa (`semantic_support_used == True`), cổng tự động cứu viện (rescue) câu hỏi, không kích hoạt veto cứng `final_evidence_query_coverage_below_threshold`.
- Chỉ khi **cả hai kênh cùng đồng thuận thất bại** (Lexical trượt VÀ Dense Semantic không đạt) thì cổng mới kích hoạt chặn cứng. Điều này giải thích tại sao tỷ lệ chặn đúng của cổng đạt mức hoàn hảo 100% trên nhóm câu chẩn đoán ngắn.

---

## 2. Mục 1: Đo phân bố thực tế từ các tệp dữ kiện đo đã có

### 2.1. Thống kê lịch sử chặn qua 5 đợt đo

Đối soát từ 5 tệp dữ kiện thô trong kho:
1. `rows-synth-claimbudget-x2.jsonl`: 4 câu bị chặn (`Q0824`, `Q0704`, `Q0718`, `Q0668`).
2. `rows-synth-claimbudget-apply.jsonl`: 4 câu bị chặn (`Q0824`, `Q0704`, `Q0718`, `Q0668`).
3. `rows-synth-intent-classify.jsonl`: 8 câu bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0695`, `Q0668`, `Q0843`).
4. `rows-synth-fallback-citation-fix.jsonl`: 8 câu bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0695`, `Q0668`, `Q0843`).
5. `rows-synth-context-entity-home.jsonl`: 8 câu bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0695`, `Q0668`, `Q0843`).

Tổng số mã câu từng bị chặn trong toàn bộ lịch sử là **10 câu duy nhất**:
- `Q0704` và `Q0718` từng bị chặn ở đợt cũ do dạng câu hỏi chưa được gán `diagnosis`. Khi phân loại đúng `diagnosis` và kích hoạt retrieval chuyên biệt, cả hai câu này đều đạt độ phủ từ khóa ≥ 0.60 (`Q0704` đạt 0.625, `Q0718` đạt 0.647) và đã thông cổng thành công, không còn bị chặn.
- Ở 3 đợt đo gần nhất, danh sách câu bị chặn ổn định tuyệt đối ở **8 câu**.

### 2.2. Bảng phân bố chi tiết 10 câu từng bị chặn

| STT | Mã câu | Độ dài (ký tự) | Số từ | Phân nhóm độ dài | Dạng câu hỏi | Độ phủ từ khoá (`final_cov`) | Best Cov | Chế độ phục vụ | Lý do chặn cứng (`hard_reasons`) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | **Q1034** | 18 | 2 | **Ngắn (< 50)** | diagnosis | **0.125** | 0.125 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 2 | **Q0850** | 26 | 1 | **Ngắn (< 50)** | diagnosis | **0.214** | 0.214 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 3 | **Q0620** | 34 | 7 | **Ngắn (< 50)** | diagnosis | **0.250** | 0.250 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 4 | **Q0668** | 36 | 9 | **Ngắn (< 50)** | diagnosis | **0.250** | 0.250 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 5 | **Q0824** | 43 | 1 | **Ngắn (< 50)** | diagnosis | **0.103** | 0.000 | `abstain` | `no_target_query_evidence`, `no_direct_query_evidence`, `final_evidence_query_coverage_below_threshold` |
| 6 | **Q0843** | 48 | 10 | **Ngắn (< 50)** | diagnosis | **0.400** | 0.500 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 7 | **Q0849** | 49 | 11 | **Ngắn (< 50)** | diagnosis | **0.545** | 0.545 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 8 | **Q0695** | 74 | 17 | **Dài (≥ 50)** | diagnosis | **0.571** | 0.571 | `abstain` | `final_evidence_query_coverage_below_threshold` |
| 9 | **Q0704** | 73 | 15 | **Dài (≥ 50)** | diagnosis | **0.625** | 0.625 | `answer_with_limits` | *(Không bị chặn — thông cổng)* |
| 10 | **Q0718** | 79 | 16 | **Dài (≥ 50)** | diagnosis | **0.647** | 0.647 | `answer_with_limits` | *(Không bị chặn — thông cổng, đạt 3.0đ)* |

---

## 3. Mục 2: Chấm lại bằng tay có căn cứ toàn bộ mẫu câu bị chặn

Tiến hành đọc bằng tay toàn bộ các mẩu bằng chứng truy hồi (`items`) được trích xuất trực tiếp từ chỉ mục thực tế `library.sqlite` đối với 8 câu bị chặn ở lượt đo hiện hành:

### 3.1. Nhóm câu chẩn đoán ngắn (< 50 ký tự — 7 câu)

#### 1. Câu `Q0620` (34 ký tự — Độ phủ: 0.250)
- **Câu hỏi:** `2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。`
- **Từ khóa kỳ vọng (Rubric):** `['49.49%', '25.42%', 'BOWSKEW 4 BEAM']`
- **Bằng chứng truy hồi được (7 mẩu):**
  - Mẩu [1] & [4] & [5]: Các dòng văn bản OCR lỗi font (`wsc-*.txt`) từ bảng lương/vật tư không chứa tỷ lệ NG.
  - Mẩu [2] & [3]: Báo cáo `Sirius 2 _ C7620_報告版 4.pptx` nói về Bowskew治具 và lỗi C7620 ngày 19/2, không có dữ liệu tháng 3/2026.
  - Mẩu [6] & [7]: Excel `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` kích thước phôi ngày 18/8.
- **Đánh giá:** Không có bất kỳ mẩu nào chứa tỷ lệ `49.49%` hay `25.42%`.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 2. Câu `Q0668` (36 ký tự — Độ phủ: 0.250)
- **Câu hỏi:** `g1 và g2 có nominal và giới hạn nào?`
- **Từ khóa kỳ vọng (Rubric):** `['10.45', '11.85', '10.25', '12.05']`
- **Bằng chứng truy hồi được (12 mẩu):**
  - Mẩu [1] & [4]: File Excel ghi nhận lỗi serial `Write DP Serial NG.xlsx`.
  - Mẩu [2], [3], [5], [6], [8], [9], [10], [12]: Sơ đồ mạch điện PDF (`MAIN_3V2XC47010_04.pdf`, `DMT回路図.pdf`) chứa các chân tín hiệu bus bộ nhớ (`DQSU_T`, `LDQS_C`).
  - Mẩu [7]: Báo cáo `Sirius 2` nhắc đến mã khuôn `122-g1 122-g2` nhưng không có thông số nominal.
- **Đánh giá:** Hoàn toàn không có các con số kích thước và giới hạn `10.45`, `11.85`, `10.25`, `12.05`.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 3. Câu `Q0824` (43 ký tự — Độ phủ: 0.103)
- **Câu hỏi:** `61C1068E7022は8月12日と13日で判定Patternが変わりましたか。`
- **Từ khóa kỳ vọng (Rubric):** `['Total', 'Cyan', 'Yellow']`
- **Bằng chứng truy hồi được (8 mẩu):**
  - Mẩu [1] & [2]: Tọa độ đo XY `tổng_hợp_dữ_liệu_XY_Target_2021.04.12.xlsx` từ năm 2021.
  - Mẩu [3]: Mạch điện `Iris_2ND_IH_MP_01基板回路図`.
  - Mẩu [5]: Bảng đo `matome.xlsx` của serial khác `61C1068D8813`.
  - Mẩu [7]: Email nhắc `#7022` đo được nhưng không có dữ liệu so sánh ngày 12 và 13/8.
- **Đánh giá:** Không có dữ liệu so sánh Pattern phán định của serial `61C1068E7022` giữa hai ngày 12/8 và 13/8.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 4. Câu `Q0843` (48 ký tự — Độ phủ: 0.400)
- **Câu hỏi:** `Cặp giới hạn Current phổ biến nhất là bao nhiêu?`
- **Từ khóa kỳ vọng (Rubric):** `['370 mA', '520 mA', '4.399 record']`
- **Bằng chứng truy hồi được (8 mẩu):**
  - Mẩu [1] - [8]: File `Loi KDTPS.xlsx` và `Iris2020_Cコール自己診断.xlsx` nói về giới hạn trên/dưới của khay nâng thang máy (`MAIN TRAY`, `Motor Lift 1/2`) và sensor giới hạn.
- **Đánh giá:** Bộ truy hồi bị nhầm từ tiếng Anh "Current" (dòng điện laser LD) sang nghĩa "giới hạn hiện tại" của công tắc hành trình thang máy cơ khí. Hoàn toàn không có dữ liệu về dòng điện `370 mA` hay `520 mA`.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 5. Câu `Q0849` (49 ký tự — Độ phủ: 0.545)
- **Câu hỏi:** `File có bao nhiêu record lỗi và phạm vi ngày nào?`
- **Từ khóa kỳ vọng (Rubric):** `['3.153 record', '2026/08/01', '2026/08/25', '1.252 Serial']`
- **Bằng chứng truy hồi được (3 mẩu):**
  - Mẩu [1]: Ghi chú quy trình xuất kho `wsc-1e085174af345d01afbf88d6.txt`.
  - Mẩu [2] & [3]: Các dòng lỗi cá biệt về đồ gá JIG quá nhiệt trong `Loi KDTPS.xlsx`.
- **Đánh giá:** Hoàn toàn không truy hồi được sheet thống kê toàn cục chứa tổng số `3.153 record` và phạm vi ngày `2026/08/01` đến `2026/08/25`. Nếu gửi ra mô hình, mô hình chắc chắn sẽ bịa số record hoặc từ chối.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 6. Câu `Q0850` (26 ký tự — Độ phủ: 0.214)
- **Câu hỏi:** `Yellow、Cyan、Magenta分别有多少件？`
- **Từ khóa kỳ vọng (Rubric):** `['1304件', '1035件', '814件']`
- **Bằng chứng truy hồi được (8 mẩu):**
  - Mẩu [1] - [8]: `DATA_Matome.xlsx`, `Bow_Skew.xlsm`, `Sirius2_7620.xlsx` chứa tiêu đề cột có tên 3 màu `Yellow`, `Cyan`, `Magenta`.
- **Đánh giá:** Chỉ có tên màu ở tiêu đề bảng, hoàn toàn không có bảng tổng hợp số lượng lỗi theo từng màu (`1304件`, `1035件`, `814件`).
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

#### 7. Câu `Q1034` (18 ký tự — Độ phủ: 0.125)
- **Câu hỏi:** `哪一天Error Record最多？`
- **Từ khóa kỳ vọng (Rubric):** `['2026/08/11', '34笔', '08/12=22', '08/18=16']`
- **Bằng chứng truy hồi được (7 mẩu):**
  - Mẩu [1] & [2]: Tiêu đề cột bảng lịch sử `History KDTPS`.
  - Mẩu [3] - [7]: Báo cáo điều tra lỗi đơn lẻ các ngày `2026-07` và năm 2025.
- **Đánh giá:** Không truy hồi được bảng thống kê tần suất lỗi theo ngày của tháng 8/2026 để xác định ngày `2026/08/11` có `34笔`.
- **Kết luận:** **BẰNG CHỨNG KHÔNG ĐỦ**. Cổng chặn là **CHẶN ĐÚNG (True Negative)**.

---

### 3.2. Nhóm câu chẩn đoán dài (≥ 50 ký tự — 1 câu)

#### 8. Câu `Q0695` (74 ký tự — Độ phủ: 0.571)
- **Câu hỏi:** `Dữ liệu hiện tại ủng hộ lỗi chung của 1004 và 1035 hay lỗi riêng của 1035?`
- **Từ khóa kỳ vọng (Rubric):** `['1035']`
- **Bằng chứng truy hồi được (10 mẩu):**
  - Mẩu [1], [2], [6]: Báo cáo lỗi đồ gá `2ND-1035` trong `Loi KDTPS.xlsx`.
  - Mẩu [3], [5], [7], [10]: Bài thuyết trình `Y_BeamH_Camera 140_to bất thường.pptx` ghi rõ:
    > *"Tại vị trí Camera +140 của Jig Bow_Skew 1035 đường kính tia Beam đang có dấu hiệu to lên ở vùng đánh giá... Vấn đề này không phát sinh ở Jig 1004... Kết quả đo NanoScan khớp với Jig Bow_Skew 1004 => Cần tương quan lại Jig Bow_Skew 1035."*
- **Đánh giá:** Bằng chứng truy hồi được là **HOÀN TOÀN ĐẦY ĐỦ 100%** và cực kỳ sắc bén để trả lời: dữ liệu ủng hộ lỗi riêng của đồ gá 1035 (Jig 1004 chuẩn khớp với NanoScan).
- **Nguyên nhân bị chặn oan:**
  - Tập từ khóa mục tiêu (`target_terms`) trích xuất từ câu hỏi gồm 14 từ: `['dữ', 'liệu', 'hiện', 'tại', 'ủng', 'hộ', 'lỗi', 'chung', 'của', '1004', 'và', '1035', 'hay', 'riêng']`.
  - Các từ nối tiếng Việt như `ủng`, `hộ`, `chung`, `riêng`, `hay`, `và` không xuất hiện trong các đoạn trích tiếng Nhật/kỹ thuật, kéo độ phủ xuống `8/14 = 0.5714` (thiếu đúng 0.0286 để đạt ngưỡng 0.60).
- **Kết luận:** **BẰNG CHỨNG ĐỦ**. Đây là trường hợp **CHẶN OAN DUY NHẤT (False Negative)** trong toàn bộ 50 câu. Tuy nhiên câu này dài **74 ký tự**, thuộc nhóm câu phức hợp so sánh dài, hoàn toàn không phải câu chẩn đoán ngắn.

---

## 4. Mục 3: Mô phỏng hạ ngưỡng độ phủ trên dữ kiện thực tế

Tiến hành mô phỏng thực nghiệm: nếu áp dụng chính sách hạ ngưỡng `min_final_evidence_term_coverage` cho riêng nhóm câu chẩn đoán ngắn (< 50 ký tự) xuống các mức ứng viên:

| Mức ngưỡng thử nghiệm | Số câu chẩn đoán ngắn được thả | Danh sách các câu được thả | Số câu có BẰNG CHỨNG ĐỦ | Số câu có BẰNG CHỨNG THIẾU | Tỷ lệ thả lọt sai | Đánh giá an toàn |
|:---:|:---:|---|:---:|:---:|:---:|---|
| **0.50** | 1 / 7 | `Q0849` (cov=0.545) | 0 câu | **1 câu** (`Q0849`) | **100.0%** | **KHÔNG SẠCH**: Thả lọt câu thiếu số record và phạm vi ngày |
| **0.35** | 2 / 7 | `Q0849`, `Q0843` (cov=0.400) | 0 câu | **2 câu** (`Q0849`, `Q0843`) | **100.0%** | **KHÔNG SẠCH**: Thả lọt thêm câu nhầm dòng điện laser sang công tắc thang máy |
| **0.20** | 5 / 7 | `Q0849`, `Q0843`, `Q0620` (0.250), `Q0668` (0.250), `Q0850` (0.214) | 0 câu | **5 câu** | **100.0%** | **KHÔNG SẠCH**: Thả lọt hàng loạt câu hoàn toàn không có bảng số liệu |
| **0.10** | 7 / 7 | Toàn bộ 7 câu ngắn | 0 câu | **7 câu** (100%) | **100.0%** | **KHÔNG SẠCH**: Mất hoàn toàn chức năng của chốt chặn an toàn |

### Ma trận nhầm lẫn (Confusion Matrix) của nhóm câu chẩn đoán ngắn:
- **True Negatives (Bằng chứng thiếu & Cổng chặn đúng):** `7 / 7 câu (100.0%)`
- **False Negatives (Bằng chứng đủ & Cổng chặn oan):** `0 / 7 câu (0.0%)`
- **True Positives (Bằng chứng đủ & Cổng thả):** `0 câu`
- **False Positives (Bằng chứng thiếu & Cổng thả lọt):** `0 câu` (khi giữ ngưỡng 0.60) -> Tăng lên `1 đến 7 câu` nếu hạ ngưỡng!

> **KẾT LUẬN MỤC 3:**
> Giả thuyết ban đầu cho rằng *"câu hỏi chẩn đoán ngắn đang bị chặn oan do ít từ khoá"* đã bị dữ liệu thực tế phủ định 100%. Toàn bộ các câu ngắn bị chặn đều do bộ truy hồi không tìm thấy dữ liệu nguồn thực tế. Hạ ngưỡng cho nhóm câu chẩn đoán ngắn sẽ trực tiếp phá hủy độ tin cậy của hệ thống và gây ra lỗi ảo giác. Kết quả mô phỏng là **KHÔNG SẠCH**.

---

## 5. Mục 4: Thực thi Bước 4 theo hợp đồng vé

### 5.1. Quyết định kỹ thuật: Giữ nguyên ngưỡng 0.60

Tuân thủ nghiêm ngặt điều khoản quy định tại Bước 4:
*"Nếu bước 3 không sạch: không áp gì cả, báo cáo kết luận giữ nguyên ngưỡng kèm dữ kiện."*
- Hệ thống **KHÔNG THAY ĐỔI** giá trị `min_final_evidence_term_coverage = 0.60` trong [`src/aios_habit/rag_v2/evidence.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/evidence.py).
- Không phát sinh nguy cơ hồi quy và không cần chạy lại lượt đo LLM tốn kém khi mô phỏng đã chứng minh hạ ngưỡng là sai lầm.

### 5.2. Đề xuất kiến trúc giải quyết ca oan `Q0695` cho Điều phối Muse

Trường hợp mất 3.0 điểm của `Q0695` là ca oan có thật, nhưng nguyên nhân **không nằm ở ngưỡng 0.60 hay câu chẩn đoán ngắn**, mà nằm ở **khâu phân tách từ khoá tiếng Việt (`extract_content_terms`)**:
- Câu hỏi `Q0695`: `"Dữ liệu hiện tại ủng hộ lỗi chung của 1004 và 1035 hay lỗi riêng của 1035?"`
- Bộ tách từ hiện tại coi các từ dừng / từ nối tiếng Việt (`ủng`, `hộ`, `của`, `hay`, `và`, `chung`, `riêng`) là các từ khoá mục tiêu độc lập.
- **Khuyến nghị cho vé tương lai:** Bổ sung danh sách Vietnamese Stopwords trong hàm `extract_content_terms` (`src/aios_habit/rag_v2/query_planning.py`). Khi loại bỏ các từ dừng, tập từ khoá mục tiêu của `Q0695` chỉ còn: `{'dữ liệu', '1004', '1035', 'lỗi'}` -> 100% các từ này đều khớp hoàn hảo trong bằng chứng truy hồi -> Độ phủ đạt `1.0 (100%)` -> Giải cứu trọn vẹn `Q0695` mà không cần hạ bất kỳ ngưỡng an toàn nào!

---

## 6. Bảng phân bố toàn cảnh 50 câu RAG LSU (Đo trên chỉ mục production)

> Trích xuất từ tệp kiểm toán `docs/phieu-viec/ket-qua/ket-qua-synth-evidence-gate-audit-home.json`:

- **Tổng số câu đo:** 50 câu.
- **Điểm trung bình độ phủ toàn bộ đề:** `0.518 (51.8%)` (Min: 0.083, Max: 1.000).
- **Phân bố chế độ phục vụ của Evidence Gate:**
  * `answer_with_limits`: **40 / 50 câu (80.0%)** (trong đó 21 câu có độ phủ < 0.60 nhưng được kênh Semantic Dense cứu viện thành công).
  * `abstain` (chặn không gọi mô hình): **8 / 50 câu (16.0%)** (gồm 7 câu ngắn thiếu bằng chứng thật và 1 câu dài vướng từ dừng tiếng Việt).
  * `answer` (độ phủ tuyệt đối không cảnh báo): **2 / 50 câu (4.0%)**.

---

## 7. Bảng kê khai kích thước tệp đĩa thật (Lấy bằng lệnh `Get-Item`)

> Kích thước được đo đạc trực tiếp bằng PowerShell `Get-Item`, bảo đảm khớp 100% từng byte với hệ thống tệp đĩa cứng:

| Tên tệp trong `docs/phieu-viec/ket-qua/` | Loại tệp | Kích thước thật trên đĩa (Bytes) | Mục đích & Nội dung |
|:---|:---:|:---:|:---|
| `ket-qua-synth-evidence-gate-audit-home.json` | JSON | **149.473** (đo git blob size nộp kho; 152.097 byte đĩa Windows CRLF) | Dữ liệu kiểm toán chi tiết 10 câu, mẩu bằng chứng trích lục và phân bố toàn cảnh 50 câu |
| `synth-evidence-gate-audit-home.md` | Markdown | **24.783** | Báo cáo kiểm định toàn diện, phân tích bằng chứng bằng tay và chứng minh mô phỏng không sạch |

---

## 8. Cổng kiểm định chất lượng repo (Quality Gates)

Trước khi đóng vé, toàn bộ 4 cổng kiểm định nghiêm ngặt của repo được xác thực bằng lệnh thực tế:

1. **Kiểm tra biên dịch mã nguồn:**
   - Lệnh: `uv run --no-sync --group dev python -m compileall src tests`
   - Kết quả: **PASS 100%** (0 lỗi cú pháp).
2. **Kiểm thử đơn vị liên quan:**
   - Lệnh: `uv run --no-sync --group dev pytest tests/test_rag_v2_evidence.py tests/test_rag_v2_synthesis.py -q`
   - Kết quả: **88 passed in 1.19s** (100% PASS).
3. **Kiểm toán dự án tự động:**
   - Lệnh: `uv run --no-sync --group dev python -m aios_habit.cli audit`
   - Kết quả: `"status": "PASS"`.
4. **Kiểm tra nhập module ứng dụng Workspace Chat:**
   - Lệnh: `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`
   - Kết quả: **IMPORT THÀNH CÔNG (Exit code 0)**.

---

## 9. Bàn giao

Vé `SYNTH-EVIDENCE-GATE-AUDIT-HOME` đã hoàn thành 100% các yêu cầu:
- Trích xuất phân bố thực tế từ các tệp dữ kiện đo đã có cho toàn bộ các câu từng bị chặn.
- Chấm lại bằng tay có căn cứ chi tiết từng mẩu bằng chứng cho tất cả các câu bị chặn.
- Mô phỏng hạ ngưỡng và chứng minh kết quả không sạch (thả lọt 100% câu thiếu bằng chứng).
- Tuân thủ nghiêm ngặt Bước 4: giữ nguyên ngưỡng an toàn 0.60, bảo toàn kiến trúc fail-closed.
- Nộp đầy đủ tệp dữ liệu chi tiết JSON và báo cáo nghiệm thu.

Kính trình Điều phối Muse xem xét duyệt nghiệm thu.
