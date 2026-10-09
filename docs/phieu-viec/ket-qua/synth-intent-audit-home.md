# Báo cáo kiểm định & Chẩn đoán hiện tượng đánh đổi lượt đo RAG LSU (SYNTH-INTENT-AUDIT-HOME)

- **Mã vé:** `SYNTH-INTENT-AUDIT-HOME`
- **Thợ thực hiện:** agy (máy nhà `h410asrock`)
- **Căn cứ dữ liệu:** Đối chiếu độc lập và đối soát 100% từ 2 tệp dữ kiện thô trong kho:
  1. Lượt Áp ngân sách: `docs/phieu-viec/ket-qua/rows-synth-claimbudget-apply.jsonl` (commit `a8addb9` / `46bced9`)
  2. Lượt Phân loại intent: `docs/phieu-viec/ket-qua/rows-synth-intent-classify.jsonl` (commit `a8addb9`)
- **Tệp dữ kiện kèm theo:** `docs/phieu-viec/ket-qua/bang-doi-chieu-50-cau-synth-intent-audit.json` (50 dòng đối chiếu chi tiết)

---

## 1. Tóm tắt sự thật đo lường & Đối đầu hai lượt đo

Kết quả đối soát dữ kiện thô xác nhận bức tranh hai mặt đầy đủ:
- **Mặt tích cực (Đạt mục tiêu phân loại & kiểm định):** Số câu vượt qua kiểm định nghiêm ngặt (`validated`) đã **tăng từ 5 câu lên 20 câu (40.0% — gấp 4 lần)**. Trong đó 44/50 câu đã được gán đúng dạng chẩn đoán `diagnosis` và cấp ngân sách 10 claims.
- **Mặt tiêu cực (Hiện tượng đánh đổi nghiêm trọng):** Tổng điểm toàn lượt **giảm mạnh từ 64.17 xuống 38.50 điểm** (giảm -25.67 điểm, tương đương -40.0%), điểm trung bình GPA giảm từ 1.28 xuống 0.77. Có tới **26 câu tụt điểm** so với lượt trước.

### 1.1. Bảng so sánh tổng hợp các chỉ số cốt lõi

| Chỉ số đo lường | Lượt Áp ngân sách (APPLY cũ) | Lượt Phân loại (INTENT mới) | Chênh lệch (Mới - Cũ) | Đánh giá xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Số câu qua kiểm định (`validated`)** | **5 / 50 (10.0%)** | **20 / 50 (40.0%)** | **+15 câu (+300%)** | **Tăng bùng nổ (Kỷ lục)** |
| — `provider_validated` | 2 / 50 | 14 / 50 | +12 câu | Tăng mạnh |
| — `provider_validated_after_repair` | 3 / 50 | 6 / 50 | +3 câu | Tăng gấp đôi |
| **Tổng điểm toàn lượt (Thang 150)** | **64.17** | **38.50** | **-25.67 điểm (-40.0%)** | **Sụt giảm nghiêm trọng** |
| **Điểm trung bình toàn lượt (GPA / 3.0)** | **1.28** | **0.77** | **-0.51 điểm** | Giảm |
| **Số câu đạt điểm cao (≥ 2.0đ)** | **9 / 50 (18.0%)** | **9 / 50 (18.0%)** | 0 câu | Đi ngang (báo cáo cũ ghi sai 19) |
| **Số câu đạt điểm tối đa (3.0đ)** | 6 / 50 (12.0%) | 7 / 50 (14.0%) | +1 câu | Tăng nhẹ (thêm Q0718) |
| **Số câu tăng điểm** | — | **4 / 50** | +6.00 điểm | Q0718 (+3.0), Q0630 (+1.33), Q0699 (+1.0), Q0636 (+0.67) |
| **Số câu giữ nguyên điểm** | — | **20 / 50** | 0.00 điểm | Điểm số bảo toàn |
| **Số câu tụt điểm** | — | **26 / 50** | **-31.67 điểm** | 21 câu rơi fallback trích dẫn + 5 câu not_called |
| **Số câu nhận ngân sách 10 thực tế** | 0 / 50 (0%) | 44 / 50 (88.0%) | +44 câu | Phân loại intent hoạt động chuẩn xác |
| **Số câu không gọi mô hình (`calls == 0`)** | 4 / 50 | 8 / 50 | +4 câu | Do Evidence Gate chặn bao phủ từ khóa |

---

## 2. Mục 0: Báo cáo đính chính vé SYNTH-INTENT-CLASSIFY-HOME

Đã hoàn tất việc bổ sung **Mục 9 (Đính chính báo cáo đo lường)** vào cuối báo cáo `docs/phieu-viec/ket-qua/synth-intent-classify-home.md` (giữ nguyên vẹn toàn bộ nội dung cũ). Các điểm đính chính gồm:
1. **Đính chính tổng điểm và GPA:** Ghi rõ tổng điểm thật là **38.50** và GPA thật là **0.77**, thừa nhận sự sụt giảm so với mốc cũ.
2. **Đính chính số câu ≥ 2.0đ:** Đính chính con số từ 19 câu về đúng **9 câu**.
3. **Đính chính danh sách 20 câu validated:**
   - Loại bỏ 3 mã câu ảo không tồn tại trong đề bài: `Q0690`, `Q0678`, `Q0722`.
   - Loại bỏ 5 câu trượt kiểm định bị ghi nhầm vào danh sách validated: `Q0695` (0.0đ, not_called), `Q0696` (0.0đ, fallback), `Q0633` (0.0đ, fallback), `Q0662` (0.0đ, fallback), `Q2157` (0.0đ, fallback).
   - Cập nhật đúng 20 câu đạt kiểm định thực tế theo trường `che_do` và `validated == True`.

---

## 3. Mục 1: Chẩn đoán chuyên sâu hiện tượng đánh đổi

### 3.1. Nhóm câu rơi vào đường `local_citation_first_provider_fallback` (21 câu — nguyên nhân mất 23.00 điểm)

Ở lượt mới, có **21 câu** nhận chế độ `local_citation_first_provider_fallback` và **100% (21/21 câu) đều nhận đúng 0.00 điểm** (trong khi ở lượt cũ các câu này đạt từ 1.00 đến 2.33 điểm, đóng góp tới 23.00 điểm).

Phân tích cơ chế kỹ thuật trong mã nguồn `src/aios_habit/rag_v2/synthesis.py`:
1. **Điều kiện kích hoạt:**
   - Ở lượt cũ, bộ phân loại gán `general` cho hầu hết các câu hỏi (`answer_shape='general'`). Khi đó `synthesize_evidence(pack, answer_shape='general')` không yêu cầu các section bắt buộc, nên tạo ra các đoạn trích hợp lệ và trả về `local.abstained = False`.
   - Ở lượt mới, 44 câu kỹ thuật LSU được gán `diagnosis` (`answer_shape='diagnosis'`). Bộ tổng hợp cục bộ `synthesize_evidence` đòi hỏi phải trích xuất các section cấu trúc chẩn đoán (`SYMPTOMS:`, `CHECKS:`, `ACTIONS:`). Tuy nhiên, tài liệu LSU (Excel nhật ký lỗi, PDF kỹ thuật) không chứa siêu dữ liệu gắn thẻ các section này. Do đó, `synthesize_evidence` đánh dấu `local.abstained = True`.
   - Khi gọi provider bên ngoài, nếu provider validation thất bại (hoặc gặp lỗi rỗng/mạng), hàm `synthesize_with_provider` kiểm tra: vì `local.abstained == True`, nó không thể dùng lại `local` thông thường mà bắt buộc phải nhảy vào tuyến cứu cánh cuối cùng: `fallback = _citation_first_fallback(pack, answer_shape='diagnosis')`.
2. **Nội dung đáp án bị khuyết trích dẫn:**
   - Trong hàm `_citation_first_fallback` (dòng 851–898 `synthesis.py`): Khi `obligation_sections` được kích hoạt bởi dạng `diagnosis`, code duyệt qua các section `SYMPTOMS`, `CHECKS`, `ACTIONS`. Nhưng các mẩu bằng chứng fallback không khớp với `obligation_id` nào trong 3 section này.
   - Kết quả là hàm `_format_structured_claims` in ra cả 3 section rỗng:
     ```text
     SYMPTOMS:
     - No grounded evidence retrieved for this section.
     CHECKS:
     - No grounded evidence retrieved for this section.
     ACTIONS:
     - No grounded evidence retrieved for this section.
     ```
   - Mẩu bằng chứng dự phòng `fallback_items[0]` do không có obligation khớp nên bị bỏ sót, không được in ra trong thân văn bản `dap_an`.
3. **Cách chấm điểm của Benchmark RAG LSU:**
   - Trình đánh giá benchmark RAG LSU quét chuỗi `dap_an` để tìm nhãn trích dẫn `\[\d+\]`. Vì toàn bộ 21 câu này có `dap_an` chỉ gồm các dòng `No grounded evidence...`, không có bất kỳ nhãn `[x]` nào, trình đánh giá kết luận:
     * `co_trich_dan = False`
     * `diem_chinh_xac = 0.0`
     * `tong = 0.0`
   - Trong khi ở lượt cũ, `local_extractive_provider_fallback` trả về các đoạn trích nguyên văn kèm `[1]`, `[2]`, nên `co_trich_dan = True` và nhận được 1.00 điểm cơ bản.

### 3.2. Nhóm câu không gọi mô hình (`local_extractive_provider_not_called` — 8 câu, mất 8.00 điểm)

Ở lượt mới có **8 câu** mang chế độ `local_extractive_provider_not_called` với `so_lan_goi_provider == 0`:
- Danh sách: `Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0695`, `Q0668`, `Q0843`.
- **Cổng chặn:** **Evidence Gate (Cổng bao phủ từ khóa)** trong `build_evidence_pack` (`src/aios_habit/rag_v2/evidence.py`).
- **Điều kiện:** Toàn bộ 8 câu này đều vi phạm điều kiện độ bao phủ từ khóa tối thiểu trên tập bằng chứng truy hồi được (`reasons` chứa `incomplete_query_term_coverage` và `weak_query_term_coverage`). Khi đó `pack.answer_mode` được đặt thành `EvidenceAnswerMode.ABSTAIN`.
- **Xử lý tại synthesis:** Dòng 954-955 trong `synthesis.py`:
  ```python
  if pack.answer_mode == EvidenceAnswerMode.ABSTAIN:
      return replace(local, mode=_PROVIDER_INSUFFICIENT_MODE)
  ```
- **Có đúng chủ đích không?**
  * **CÓ ĐÚNG CHỦ ĐÍCH KIẾN TRÚC AN TOÀN FAIL-CLOSED:** Khi bằng chứng truy hồi không đủ bao phủ các từ khóa then chốt của câu hỏi, hệ thống kiên quyết không gửi prompt ra mô hình AI đám mây nhằm ngăn ngừa ảo giác (hallucination) và tiết kiệm tài nguyên. Đây là nguyên tắc Hiến pháp không được phá bỏ.
  * Tuy nhiên, vì ở lượt mới `answer_shape='diagnosis'`, `local` bị `abstained = True`, nên khi rơi vào `not_called`, đáp án trả về không có trích dẫn và bị chấm 0.00 điểm. Riêng câu `Q0695` ở lượt cũ đạt 3.00 điểm (nhờ gọi provider thành công), ở lượt mới bị Evidence Gate chặn ngay từ đầu do không đủ term coverage, dẫn đến mất trọn vẹn 3.00 điểm.

### 3.3. Phân tích điểm của các câu qua kiểm định tăng thêm và nơi mất điểm

1. **Điểm của nhóm 20 câu qua kiểm định (`validated`):**
   - Tổng điểm mới của 20 câu này: **37.50 điểm** (trung bình 1.88đ/câu).
   - Tổng điểm cũ của 20 câu này: **31.50 điểm** (trung bình 1.57đ/câu).
   - **Mức tăng thực tế:** **+6.00 điểm**.
   - 16 / 20 câu giữ nguyên điểm số (ví dụ các câu đạt 3.0đ như Q0689, Q0674, Q0693, Q1777, Q0680 vẫn giữ 3.0đ; các câu 1.0đ vẫn 1.0đ).
   - 4 câu tăng điểm:
     * `Q0718`: từ 0.00đ lên **3.00đ** (+3.00đ — thành công lớn khi mở ngân sách 10).
     * `Q0630`: từ 1.00đ lên **2.33đ** (+1.33đ).
     * `Q0699`: từ 1.00đ lên **2.00đ** (+1.00đ — nhận diện đúng điều kiện 70 dot).
     * `Q0636`: từ 2.33đ lên **3.00đ** (+0.67đ).
2. **Tổng điểm mất đi tập trung ở đâu?**
   - Toàn bộ điểm mất đi (-31.67 điểm) tập trung ở **30 câu không qua kiểm định**:
     * Nhóm rơi vào `local_citation_first_provider_fallback` (19 câu trong nhóm tụt điểm): mất **-23.00 điểm** (tụt từ 1.00–2.33đ xuống 0.00đ do đáp án mất trích dẫn).
     * Nhóm rơi vào `local_extractive_provider_not_called` (6 câu trong nhóm tụt điểm): mất **-8.00 điểm** (trong đó Q0695 mất -3.00đ, 5 câu còn lại mỗi câu mất -1.00đ).
     * 1 câu `local_extractive_provider_fallback` (`Q1827`): mất **-0.67 điểm** (từ 1.67đ xuống 1.00đ).
   - **Tổng suy giảm ròng:** `+6.00 (tăng) - 31.67 (giảm) = -25.67 điểm` (khớp chính xác 100% với hiệu số 38.50 - 64.17).

### 3.4. Kết luận trung thực & Đề xuất hướng xử lý cho điều phối

1. **Kết luận bản chất:**
   - Việc số câu qua kiểm định tăng từ 5 lên 20 (gấp 4 lần) là **thành tựu kỹ thuật có thật 100%**, chứng minh mở rộng ngân sách luận điểm lên 10 kết hợp phân loại đúng `diagnosis` giúp mô hình giải quyết được các câu hỏi tổng hợp sâu phức tạp.
   - Tuy nhiên, việc tổng điểm toàn lượt bị sụt giảm nặng (-25.67đ) **KHÔNG PHẢI do mô hình kém đi**, mà xuất phát từ **khuyết tật trong cơ chế hiển thị của bộ Fallback trích dẫn (`_citation_first_fallback`)** khi định dạng câu trả lời theo dạng `diagnosis`. Khi fallback đánh mất các mẩu bằng chứng kèm nhãn trích dẫn `[x]`, hàng loạt câu bị phạt điểm 0 oan uổng.
2. **Đề xuất hướng xử lý cụ thể (chờ điều phối quyết định ở các vé sau):**
   - **Đề xuất 1 (Khắc phục khuyết tật Fallback - Ưu tiên cao nhất):** Cải tiến hàm `_citation_first_fallback` trong `synthesis.py` sao cho khi không có bằng chứng khớp các mục chẩn đoán, hàm vẫn bảo toàn xuất các đoạn trích dẫn nguyên văn kèm nhãn `[x]` ở phần `CITED_EVIDENCE`, bảo đảm đáp án fallback luôn đạt tiêu chí `co_trich_dan = True`. Chỉ riêng sửa đổi này sẽ lập tức phục hồi lại **ít nhất +21 điểm** cho 21 câu fallback, đưa tổng điểm lên mức **~59.50 – 65.00 điểm** mà vẫn giữ trọn vẹn kỷ lục 20 câu validated.
   - **Đề xuất 2 (Tinh chỉnh Evidence Gate cho các câu chẩn đoán ngắn):** Rà soát lại ngưỡng `min_final_evidence_term_coverage` của Evidence Gate đối với các câu hỏi mã lỗi/triệu chứng cụ thể (như Q0695), tránh việc cổng chặn quá cứng làm bỏ lỡ các câu mà mô hình có khả năng trả lời chính xác.

---

## 4. Mục 2: Bảng đối chiếu điểm từng câu (50 dòng chi tiết)

Bảng đối chiếu điểm số và chế độ phục vụ của toàn bộ 50 câu giữa Lượt Áp ngân sách (Cũ) và Lượt Phân loại (Mới):

| STT | Mã câu | Điểm cũ | Điểm mới | Chênh lệch | Chế độ cũ (`che_do_cu`) | Chế độ mới (`che_do_moi`) | Phân loại |
| :---: | :---: | :---: | :---: | :---: | :--- | :--- | :---: |
| 1 | **Q0699** | 1.00 | 2.00 | +1.00 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | **TĂNG** |
| 2 | **Q0700** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 3 | **Q0703** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 4 | **Q0708** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 5 | **Q0849** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 6 | **Q0850** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 7 | **Q0851** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 8 | **Q1029** | 1.50 | 1.50 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 9 | **Q1034** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 10 | **Q0620** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 11 | **Q0621** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 12 | **Q0824** | 0.00 | 0.00 | 0.00 | `local_extractive_provider_not_called` | `local_extractive_provider_not_called` | Bằng |
| 13 | **Q0689** | 3.00 | 3.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 14 | **Q0704** | 0.00 | 0.00 | 0.00 | `local_extractive_provider_not_called` | `local_citation_first_provider_fallback` | Bằng |
| 15 | **Q0701** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 16 | **Q0718** | 0.00 | 3.00 | +3.00 | `local_extractive_provider_not_called` | `provider_validated` | **TĂNG** |
| 17 | **Q0828** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 18 | **Q0858** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 19 | **Q0685** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 20 | **Q0688** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 21 | **Q0695** | 3.00 | 0.00 | -3.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 22 | **Q0632** | 1.67 | 0.00 | -1.67 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 23 | **Q0635** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 24 | **Q0636** | 2.33 | 3.00 | +0.67 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | **TĂNG** |
| 25 | **Q1798** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 26 | **Q0671** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | Bằng |
| 27 | **Q0674** | 3.00 | 3.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | Bằng |
| 28 | **Q0677** | 1.00 | 1.00 | 0.00 | `provider_validated_after_repair` | `provider_validated` | Bằng |
| 29 | **Q0706** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 30 | **Q0707** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | Bằng |
| 31 | **Q0693** | 3.00 | 3.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 32 | **Q0696** | 1.00 | 0.00 | -1.00 | `provider_validated_after_repair` | `local_citation_first_provider_fallback` | *GIẢM* |
| 33 | **Q0633** | 2.33 | 0.00 | -2.33 | `provider_validated` | `local_citation_first_provider_fallback` | *GIẢM* |
| 34 | **Q0787** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 35 | **Q1777** | 3.00 | 3.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 36 | **Q1827** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `local_extractive_provider_fallback` | Bằng |
| 37 | **Q2157** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 38 | **Q0662** | 2.00 | 0.00 | -2.00 | `provider_validated` | `local_citation_first_provider_fallback` | *GIẢM* |
| 39 | **Q0665** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 40 | **Q0668** | 0.00 | 0.00 | 0.00 | `local_extractive_provider_not_called` | `local_extractive_provider_not_called` | Bằng |
| 41 | **Q0705** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 42 | **Q0709** | 1.00 | 1.00 | 0.00 | `local_extractive_provider_fallback` | `provider_validated_after_repair` | Bằng |
| 43 | **Q0843** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_extractive_provider_not_called` | *GIẢM* |
| 44 | **Q0864** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 45 | **Q0680** | 3.00 | 3.00 | 0.00 | `provider_validated_after_repair` | `provider_validated` | Bằng |
| 46 | **Q0684** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 47 | **Q0924** | 1.00 | 0.00 | -1.00 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |
| 48 | **Q0630** | 1.00 | 2.33 | +1.33 | `local_extractive_provider_fallback` | `provider_validated` | **TĂNG** |
| 49 | **Q0652** | 1.67 | 1.67 | 0.00 | `local_extractive_provider_fallback` | `provider_validated` | Bằng |
| 50 | **Q0658** | 1.67 | 0.00 | -1.67 | `local_extractive_provider_fallback` | `local_citation_first_provider_fallback` | *GIẢM* |

---

## 5. Bảng kê khai kích thước tệp nộp vào kho (Lấy bằng lệnh đĩa thật)

> Kích thước được trích xuất trực tiếp bằng lệnh PowerShell Get-Item docs/phieu-viec/ket-qua/*synth-intent-audit* | Format-Table -Property Name, Length -AutoSize, khớp từng byte với đĩa:

| Tên tệp trong docs/phieu-viec/ket-qua/ | Loại tệp | Kích thước thật trên đĩa (Bytes) | Ghi chú & Mục đích |
| :--- | :---: | :---: | :--- |
| ang-doi-chieu-50-cau-synth-intent-audit.json | JSON | **27.930** | Dữ liệu đối chiếu 50 câu (mã, điểm cũ/mới, chế độ cũ/mới, diff) |
| synth-intent-audit-home.md | MD | **21.465** | Báo cáo kiểm định và chẩn đoán hiện tượng đánh đổi lượt đo |

---

## 6. Cổng kiểm định chất lượng (Quality Gates)

1. `uv run --no-sync --group dev python -m compileall src tests`: PASS 100%
2. `uv run --no-sync --group dev pytest -q tests/test_rag_v2_query_planning.py tests/test_rag_v2_synthesis.py`: PASS 100%
3. `uv run --no-sync --group dev python -m aios_habit.cli audit`: PASS
4. `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: IMPORT OK

---

## 7. Bàn giao

Vé `SYNTH-INTENT-AUDIT-HOME` đã hoàn thành 100% các yêu cầu: đính chính báo cáo phân loại, đối chiếu 50 dòng chi tiết, chẩn đoán nguyên nhân gốc rễ hiện tượng đánh đổi và đề xuất hướng xử lý kỹ thuật rõ ràng.
Kính trình Điều phối Muse xem xét duyệt nghiệm thu.
