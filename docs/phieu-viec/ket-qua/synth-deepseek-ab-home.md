# Báo cáo vé SYNTH-DEEPSEEK-AB-HOME — Đo thử DeepSeek V4.1 Flash trên bộ 50 câu LSU CPU-only

- **Máy thực hiện:** NHÀ `h410asrock` (thợ agy — `gemini-3.8-flash-high`, CPU-only, không dùng GPU).
- **Thời điểm thực hiện:** 2026-10-08 22:33 – 22:58 +07.
- **Căn cứ:** User QUYẾT tại chat 2026-10-08 ~18:17 +07: "đo thử DeepSeek với máy nhà để close vòng đó đi". Bối cảnh: 3 thực nghiệm liên tiếp đã chốt trần của nhóm model miễn phí qua tuyến pool Command Code (GPA ~1,21–1,25; validated chỉ 0–2/50 mỗi model khi ép làm model chính). DeepSeek V4.1 Flash là phương án trả phí rẻ user đã duyệt làm dự phòng từ 07/10 (giá qua Command Code: $0,15 vào / $0,60 ra mỗi 1M token). Vé này đo nó trên ĐÚNG bộ đề + thang chấm + runner của các lane pool trước để so sánh ngang hàng và chốt cấu hình tổng hợp cho bản go-live.
- **Kết quả cốt lõi:** Đo đủ 50/50 câu RAG LSU CPU-only; **GPA đạt 1.26 / 3.0** (tổng điểm 63.18 / 150); **3 / 50 câu `provider_validated`** (Q0851, Q0620, Q2157); **6 / 50 câu đạt điểm tuyệt đối 3.0**; chi phí thực tế tiêu thụ **$0.092991** (chưa tới 10 xu Mỹ, xa trần $2.0); băm chỉ mục trước/sau khớp 100%.

---

## 1. Chuẩn bị tuyến & Xác nhận Model (Bước 1)

1. **Tra cứu danh sách model trên Command Code (gói GOAT):**
   - Đã gọi API endpoint `https://api.commandcode.ai/provider/v1/models` lấy danh sách 87 models được hỗ trợ.
   - Xác nhận model DeepSeek V4.1 Flash **CÓ MẶT CHÍNH THỨC** trong danh sách với mã định danh chính xác:
     `deepseek/deepseek-v4.1-flash`.
2. **Kiểm tra probe trực tiếp (Evidence-based):**
   - Chạy test probe gọi trực tiếp qua Command Code API: Phản hồi thành công `HTTP 200 OK` trong **2.41 giây**.
   - Tách bạch hoàn hảo giữa `content` ("Hà Nội là thủ đô của Việt Nam.") và `reasoning_content` (chuỗi suy luận CoT nội bộ), không bị hiện tượng rỗng content hoặc trộn lẫn như một số model free.

---

## 2. Ép làm Model chính duy nhất & Khôi phục nguyên trạng (Bước 2)

1. **Cấu hình tạm thời phục vụ lượt đo:**
   - Đã sao lưu `.env` thành `.env.backup_pre_deepseek`.
   - Cấu hình tạm thời trong `.env` và `RouterProviderConfig`:
     - `AIOS_LOCAL_AI_MODEL=deepseek/deepseek-v4.1-flash`
     - `AIOS_LOCAL_AI_FAILOVER_MODELS=` (rỗng, tắt hoàn toàn failover sang model free trong lượt đo để số đo thuần một model).
     - `allow_model_auto_substitution=False`, `max_attempts=1`, `timeout_seconds=120`.
2. **Khôi phục nguyên trạng cấu hình pool ngay sau khi đo:**
   - Sau khi hoàn thành câu 50/50, đã khôi phục nguyên vẹn tệp `.env` về cấu hình pool hiện tại:
     - `AIOS_LOCAL_AI_MODEL=inclusionai/ling-3.1-flash:free`
     - `AIOS_LOCAL_AI_FAILOVER_MODELS=poolside/laguna-s-2.1-free,inclusionai/ling-3.0-flash-sante:free`
   - Đã xóa tệp sao lưu `.env.backup_pre_deepseek`, xác nhận kiểm tra lại cấu hình khớp 100%.

---

## 3. Kết quả đo đủ 50 câu RAG LSU CPU-only (Bước 3)

- **Harness & Runner:** Tạo runner chuẩn hóa ngoài Git `C:\tmp\lsu-quality-rag-home\do_rag_50_synth_deepseek.py`.
- **Rào cứng cách ly:**
  - Thuần CPU 100%: `CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu`.
  - Bộ đếm chuẩn hóa theo trường `che_do` từ từng dòng tệp checkpoint `rows-synth-deepseek.jsonl`.
  - Reset `health_store` mỗi câu độc lập (chống cooldown khóa oan).
  - Tích hợp hook giám sát token usage từng câu và kiểm soát trần $2.0 credits.

### Bảng chỉ số tổng hợp chi tiết lượt đo DeepSeek V4.1 Flash:

| Chỉ số nghiệm thu | Giá trị đo thực tế | Ghi chú & Rào cứng |
|---|---|---|
| **Tổng số câu đo** | **50 / 50 câu** | Đủ 100% bộ đề chuẩn `cau-hoi-50.json` |
| **Tổng điểm đạt được** | **63.18 / 150** | Thang điểm Rubric chuẩn |
| **GPA trung bình** | **1.26 / 3.0** | Cao nhất trong tất cả các lượt đo Command Code |
| **Số câu Provider Validated** | **3 / 50 câu (6.0%)** | Q0851 (1.0đ), Q0620 (1.67đ), Q2157 (1.0đ) |
| **Số câu Fallback trích cục bộ** | **43 / 50 câu (86.0%)** | Fallback an toàn bảo toàn điểm số |
| **Số câu Not Called (thiếu dữ liệu)** | **4 / 50 câu (8.0%)** | Q0824, Q0704, Q0718, Q0668 (truy xuất không đủ độ phủ) |
| **Số câu không trích dẫn (uncited)** | **10 / 50 câu (20.0%)** | 80% câu trả lời có trích dẫn hợp lệ |
| **Số câu đạt điểm tối đa (3.0)** | **6 / 50 câu (12.0%)** | Q0689, Q0695, Q0674, Q0693, Q1777, Q0680 |
| **Số câu đạt khá ($\ge$ 2.0)** | **7 / 50 câu (14.0%)** | Gồm 6 câu 3.0đ + 1 câu 2.33đ (Q0636) |
| **Thời gian toàn câu (Mean / Median)** | **25.19s / 22.42s** | Trung bình số học và số giữa |
| **Thời gian tổng hợp (Mean / Median)** | **19.37s / 16.96s** | Thời gian sinh của DeepSeek |
| **Tổng token tiêu thụ** | **304,964 tokens** | Prompt: 199,974 tokens; Completion: 104,990 tokens |
| **Số credits thực tế bị trừ** | **$0.092991** | Ước tính < $0.50, thực tế chưa tới $0.10 (trần $2.0) |
| **Lỗi kỹ thuật / Crash / Rate-limit** | **0 / 50 câu (0%)** | Tuyến chạy ổn định 100% |
| **Dung lượng Index trước & sau** | `2,942,201,856` bytes | **Khớp 100% (chỉ đọc)** |
| **Băm SHA-256 Index trước & sau** | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **Khớp 100% tuyệt đối** |
| **Băm MD5 Index trước & sau** | `239009676829484049738866329de9f2` | **Khớp 100% tuyệt đối** |

---

## 4. Bảng so sánh ngang hàng & Đáp án mẫu nguyên văn (Bước 4)

### 4.1. Bảng đối chiếu ngang hàng với Pool Free và các Model Free trước:

| Chỉ số so sánh | DeepSeek V4.1 Flash | POOL Free hiện tại | Ling-3.1-flash (Lượt A) | Laguna-s-2.1 (Lượt C) | Sante (Lượt B) | Gemini cũ (8585) |
|---|---|---|---|---|---|---|
| **Tổng điểm đạt được** | **63.18 / 150** | 62.67 / 150 | 61.67 / 150 | 60.67 / 150 | 60.67 / 150 | 61.17 / 150 |
| **GPA trung bình** | **1.26 / 3.0** | 1.25 / 3.0 | 1.23 / 3.0 | 1.21 / 3.0 | 1.21 / 3.0 | 1.22 / 3.0 |
| **Provider Validated** | **3 / 50** | 1 / 50 | 2 / 50 | 2 / 50 | 0 / 50 | **9 / 50** |
| **Fallback trích cục bộ** | 43 / 50 | 47 / 50 | 46 / 50 | 46 / 50 | 48 / 50 | 41 / 50 |
| **Số câu đạt tối đa (3.0)** | **6 câu** | 5 câu | 4 câu | 4 câu | 4 câu | 4 câu |
| **Số câu đạt khá ($\ge$ 2.0)** | **7 câu** | 7 câu | 7 câu | 6 câu | 6 câu | 7 câu |
| **Độ trễ TB toàn câu** | 25.19s (med 22.4s) | ~18s | 22.28s | 15.74s | **13.01s** | ~12s |
| **Độ trễ TB Tổng hợp** | 19.37s (med 17.0s) | ~4.5s | 11.54s | 4.22s | **2.96s** | ~3.8s |
| **Tỷ lệ lỗi kỹ thuật / 429** | **0%** | 0% | 0% | 0% | Bị 429 sau 16 câu | Bị 429 gián đoạn |
| **Credits tiêu thụ** | **$0.092991** | $0.00 | $0.00 | $0.00 | $0.00 | Miễn phí proxy |

---

### 4.2. Ba đáp án mẫu nguyên văn của DeepSeek V4.1 Flash:

#### Mẫu 1: Câu đạt `provider_validated` (Q0620 — Điểm: 1.67)
- **Câu hỏi:** `2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。`
- **Đáp án nguyên văn từ DeepSeek:**
```text
**Tóm tắt:** Chưa đủ bằng chứng để xác định tỷ lệ NG của "BOWSKEW 4 BEAM" trong tháng 3/2026; các nguồn hiện có chỉ ghi dữ liệu BOW-SKEW/BEAM ở thời điểm và phạm vi khác [1][2][7].
- Nguồn [2] nêu QC cần phân tích tỷ lệ NG trên "2 BOW SKEW" theo từng JIG BEAM trong bối cảnh cuộc họp chất lượng bất thường lần 5 ngày 6/8/2026, còn nguồn [7] chỉ đề cập BOWSKEW 治具 với các giá trị chênh lệch chiều cao quang lộ (dot), không nêu tỷ lệ NG [2][7].
- Không có nguồn nào nêu tỷ lệ NG cho "BOWSKEW 4 BEAM" hoặc mốc tháng 3/2026 tương ứng; cụm "4 BEAM" không xuất hiện trong các đoạn bằng chứng [1][2][7].
- Cần tệp/báo cáo QC riêng về phân tích tỷ lệ NG theo JIG BEAM cho "2 BOW SKEW"/"4 BEAM" và kỳ tháng 3/2026, ví dụ tệp đính kèm được nhắc trong cuộc họp [2][4].
**Nguồn đã dùng:** [1], [2], [4], [7]
LIMITATIONS: incomplete_query_term_coverage, weak_query_term_coverage, weak_term_coverage
```
- **Nhận xét điều phối:** DeepSeek tuân thủ kỷ luật trích dẫn xuất sắc; nhận diện rõ ràng giới hạn bằng chứng và từ chối suy đoán an toàn, trích dẫn chuẩn `[1][2][7]`, qua trọn bộ kiểm định không lỗi.

#### Mẫu 2: Câu rơi `local_extractive_provider_fallback` (Q0700 — Điểm: 1.0)
- **Câu hỏi:** `C23とC24ではどのような発生Trendでしたか。`
- **Đáp án nguyên văn DeepSeek sinh ra trước khi fallback:**
```text
## Tóm tắt
Theo nguồn [3] (Loi KDTPS.xlsx), C23 và C24 đều ghi nhận lỗi NG liên quan đến SHUTTER phía hộp mực thải sau khi lắp TONER CONTAINER vào thân máy, trong đó tỷ lệ NG của C23L cao hơn C24L [3].

## Điều đã xác nhận
- C24L: 17/78 máy NG ~ 21,79% (NG: Y: 10 máy, M: 7 máy) [3].
- C23L: 36/98 máy NG ~ 36,73% (NG: K: 15 máy, C: 12 máy, Y: 9 máy) [3].
- Lỗi phát sinh liên tục trong các ngày 18/2, 19/2 và 20/2 [3].
```
- **Lý do fallback:** `provider_answer_claim_budget_exceeded` (DeepSeek hiểu tài liệu Excel rất sâu, trích đúng số máy NG và tỷ lệ %, nhưng do sinh 4 dòng luận điểm vượt quá ngân sách dòng claim_budget được cấp cho bằng chứng nên bị bộ kiểm định đánh trượt, hệ thống fallback về trích cục bộ để bảo toàn điểm an toàn 1.0đ).

#### Mẫu 3: Câu điểm thấp nhất (Q0824 — Điểm: 0.0)
- **Câu hỏi:** `61C1068E7022は8月12日と13日で判定Patternが変わりましたか。`
- **Chế độ:** `local_extractive_provider_not_called` (Lý do thiếu: `weak_query_term_coverage`).
- **Đáp án hệ thống trả về:**
```text
KHÔNG ĐỦ BẰNG CHỨNG:
- Corpus được truy xuất không thiết lập được sự kiện hoặc quan hệ mà câu hỏi yêu cầu.
- Cần nguồn trực tiếp (ví dụ: tài liệu quy trình, bản ghi hệ thống hoặc hàng dữ liệu có mục tiêu) trước khi có thể trả lời an toàn.
LIMITATIONS: evidence_pack_insufficient, final_evidence_query_coverage_below_threshold
```
- **Nhận xét:** Khi tầng truy hồi không tìm đủ dữ liệu khớp mã máy, hệ thống tự động ngắt không gọi provider tốn credits ($0.00), bảo toàn ngân sách.

---

## 5. Kết luận dứt khoát theo số & Đề xuất cấu hình Go-Live (Bước 5)

### 5.1. DeepSeek V4.1 Flash có vượt trội rõ rệt hay không?
**KẾT LUẬN: KHÔNG VƯỢT TRỘI RÕ RỆT Ở CHỈ SỐ GPA ĐỂ TẠO BƯỚC NHẢY VỌT (CHƯA ĐẠT GPA $\ge$ 1.5).**
- **Về GPA:** Đạt **1.26 / 3.0** — nhỉnh hơn nhẹ so với Pool Free (1.25) và các model đơn lẻ (1.21–1.23).
- **Về Validated:** Đạt **3 / 50 câu** — cải thiện gấp 3 lần Pool Free (1/50) và gấp 1.5 lần Ling-3.1 (2/50), nhưng vẫn thua xa Gemini cũ (9/50).
- **Về số câu 3.0đ:** Đạt **6 câu**, cao nhất trong toàn bộ các cấu hình.
- **Nguyên nhân cốt lõi:** Nút thắt tỷ lệ validated thấp không nằm ở năng lực mô hình (DeepSeek sinh câu trả lời tiếng Việt cực kỳ mạch lạc và hiểu sâu ngữ cảnh như ở Q0700), mà nằm ở **rào cản `claim_budget` và độ dài của bộ kiểm định WorkLens RAG v2**: Các mô hình thông minh có xu hướng diễn giải đầy đủ các khía cạnh số liệu, dẫn tới việc vượt quá số dòng luận điểm cho phép của 8 đoạn bằng chứng.

### 5.2. Đề xuất cấu hình cho bản Go-Live
Căn cứ trên số liệu thực nghiệm:
1. **KHÔNG dùng DeepSeek làm Model chính duy nhất:**
   Vì mức cải thiện GPA từ 1.25 lên 1.26 là không đủ lớn để thay thế hoàn toàn nhóm model miễn phí.
2. **KHUYẾN NGHỊ: Sử dụng DeepSeek V4.1 Flash làm "TẦNG DỰ PHÒNG CHẤT LƯỢNG CAO CÓ PHÍ" (Paid High-Quality Failover Tier):**
   - **Tầng 1 (Free Primary):** `inclusionai/ling-3.1-flash:free` (miễn phí, chất lượng free tốt nhất).
   - **Tầng 2 (Free Fast Failover):** `poolside/laguna-s-2.1-free` (miễn phí, tốc độ 4.2s, gánh tải khi tuyến 1 nghẽn).
   - **Tầng 3 (Paid Quality Failover):** `deepseek/deepseek-v4.1-flash` (khi cả 2 tuyến free đều bị rate-limit 429 hoặc lỗi kết nối, kích hoạt DeepSeek với chi phí siêu rẻ: **~$0.0018 / câu**, 1.000 câu chỉ tốn ~$1.8, bảo đảm trải nghiệm người dùng không bị gián đoạn).
   - **Tầng 4 (Deterministic Fallback):** Trích xuất cục bộ an toàn chống ảo giác.

---

## 6. Bằng chứng cổng kiểm tra chất lượng (Quality Gates)

- **Biên dịch mã nguồn (`compileall`):**
  `uv run --no-sync --group dev python -m compileall src tests` -> **PASS (Exit Code 0)**.
- **Kiểm thử Router & Synthesis Provider:**
  `uv run --no-sync --group dev pytest tests/test_ai_router.py tests/test_rag_v2_synthesis_provider.py -q` -> **56/56 PASS (100%)**.
- **Kiểm toán chất lượng (`cli audit`):**
  `uv run --no-sync --group dev python -m aios_habit.cli audit` -> **`{"errors": [], "status": "PASS", "warnings": []}`**.
- **Kiểm tra khả năng nạp Workspace Chat App:**
  `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` -> **`IMPORT_OK`**.
- **Tính toàn vẹn Index Production:**
  `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` (2,942,201,856 bytes) -> **Khớp 100% trước và sau lượt đo**.
