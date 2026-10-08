# Báo cáo vé SYNTH-CONTRACT-FREE-HOME — Thử nghiệm hợp đồng tổng hợp khắt khe cho Model Free

- **Mã vé:** `SYNTH-CONTRACT-FREE-HOME`
- **Máy thực hiện:** NHÀ `h410asrock` (thợ agy — `gemini-3.8-flash-high`).
- **Thời gian thực hiện:** 2026-10-08 10:04 – 10:23 +07.
- **Mục tiêu:** Thử nghiệm biến thể hợp đồng tổng hợp (contract prompt) "Kỷ luật trích dẫn" khắt khe cho model miễn phí (`inclusionai/ling-3.1-flash:free` — con tốt nhất từ vé A/B) nhằm kiểm chứng giả thuyết: *Liệu việc ép kỷ luật trích dẫn từng dòng, cấm mọi câu mở đầu/kết luận không trích dẫn, và giới hạn cụ thể ngân sách dòng có giúp mở khóa tỷ lệ validated mà không cần nới lỏng bộ kiểm định hay không?*

---

## 1. Cơ sở thực nghiệm & Phân tích dữ liệu thô từ vé A/B (Bước 1)

Từ 3 tệp dữ liệu kiểm chứng độc lập của vé `SYNTH-MODEL-AB-HOME` (`rows-synth-ab-a.jsonl`, `rows-synth-ab-b.jsonl`, `rows-synth-ab-c.jsonl`), thống kê chi tiết các lỗi kiểm định trên từng lượt gọi provider:

| Loại lỗi kiểm định (`validation_errors`) | Lượt A (`ling-3.1-flash`) | Lượt B (`ling-3.0-sante`) | Lượt C (`laguna-s-2.1`) |
|---|---|---|---|
| **Tổng số lượt gọi provider thực tế** | 70 lượt | 29 lượt | 15 lượt |
| `provider_answer_uncited_material_claim` | **69 / 70 (98.6%)** | **27 / 29 (93.1%)** | **14 / 15 (93.3%)** |
| `provider_answer_missing_required_limitations` | **64 / 70 (91.4%)** | **25 / 29 (86.2%)** | **9 / 15 (60.0%)** |
| `provider_answer_claim_budget_exceeded` | **62 / 70 (88.6%)** | **22 / 29 (75.9%)** | **12 / 15 (80.0%)** |
| `provider_answer_unsupported_critical_literal` | 46 / 70 (65.7%) | 14 / 29 (48.3%) | 8 / 15 (53.3%) |
| `provider_answer_missing_citations` | 0 / 70 (0.0%) | 2 / 29 (6.9%) | 2 / 15 (13.3%) |

### Quan sát mấu chốt về hành vi của Model Free:
1. **Thiên hướng chèn câu dẫn nhập tự do (Conversational Openers):** Trên 95% câu trả lời của mô hình bắt đầu bằng các câu lặp lại/dịch câu hỏi sang tiếng Anh: *"The user asks in Japanese: ...", "Looking at the sources:", "From the evidence:"*. Những dòng này không có nhãn trích dẫn `[n]`, lập tức kích hoạt lỗi `provider_answer_uncited_material_claim`.
2. **Tiêu hao ngân sách claim:** Mỗi dòng mở đầu rác này đều bị bộ đếm dòng tính là 1 claim độc lập, nhanh chóng làm vượt ngưỡng `max_claims` cho phép (`claim_budget_exceeded`).
3. **Bỏ quên vế giới hạn (`LIMITATIONS`):** Khi bằng chứng không đủ (`limitation_reasons`), mô hình thường diễn giải vòng vo thay vì xuất dòng chuẩn `LIMITATIONS: ...` ở cuối cùng.

---

## 2. Thiết kế biến thể hợp đồng "Kỷ luật trích dẫn" (Bước 2)

Biến thể hợp đồng được tích hợp trực tiếp vào `src/aios_habit/rag_v2/synthesis.py` (hàm `format_provider_synthesis_contract` và `format_provider_synthesis_repair_contract`) và được cô lập an toàn sau cờ môi trường:

- **Cờ cấu hình:** `AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT` (mặc định: **TẮT** / `False`).
- **Khi TẮT:** Trả về 100% nguyên văn chuỗi hợp đồng cũ, bảo toàn tương thích tuyệt đối cho mọi test hồi quy hiện có.
- **Khi BẬT (`1` / `true`):** Bổ sung khối chỉ dẫn kỷ luật khắt khe:
  1. `1. NO UNCITED OPENERS OR INTROS:` Cấm tuyệt đối mọi câu chào, câu dẫn, tóm tắt/dịch lại câu hỏi (*"DO NOT write conversational introductions, question restatements, or meta commentary (e.g., NEVER write 'The user asks:', 'Looking at the sources:', 'From the evidence:', or 'Here is the answer:')"*).
  2. `2. EVERY FACTUAL LINE MUST END WITH A CITATION:` Mỗi dòng/gạch đầu dòng dữ kiện BẮT BUỘC phải kết thúc bằng nhãn trích dẫn `[n]`.
  3. `3. STRICT CLAIM BUDGET:` Giới hạn số dòng tối đa cụ thể, ưu tiên viết ít dòng chắc chắn (1 đến $\min(max\_claims, 3)$ dòng) thay vì viết dài.
  4. `4. DATES AND IDENTIFIERS:` Giữ nguyên các ký tự, mã hiệu, ngày tháng từ tài liệu gốc.
  5. `MANDATORY FINAL LINE:` Yêu cầu dòng cuối cùng của toàn bộ câu trả lời BẮT BUỘC là `LIMITATIONS: {limitations}` nếu có thiếu sót.
  6. Trong hợp đồng tự sửa lỗi (`repair_contract`): Bổ sung chỉ dẫn `STRICT REPAIR DISCIPLINE` xóa sạch câu mở đầu rác và nén số dòng dưới hạn mức.

### Tuân thủ nghiêm ngặt rào cứng của Ticket:
- **CẤM nới kiểm định:** Không tăng `max_claims`, không đổi cách đếm claim, không tắt hay giảm nhẹ bất kỳ lỗi nào trong `validate_provider_synthesis_answer`, không sửa rubric.
- **Kiểm thử hồi quy:** Thêm test `test_disciplined_citation_contract_format` vào `tests/test_rag_v2_synthesis.py`; toàn bộ 109 test liên quan đều PASS 100%.

---

## 3. Bảng đối chiếu thực nghiệm: Đối chứng vs Hợp đồng kỷ luật (Bước 3)

Thực nghiệm đo đạc độc lập trên máy nhà `h410asrock`, đúng bộ 50 câu LSU, thuần CPU 100% (`CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu`), reset `health_store` mỗi câu, chỉ đọc index:

| Chỉ số đo đạc | Lượt đối chứng (Hợp đồng cũ — Lượt A vé A/B) | Lượt thử nghiệm (Hợp đồng kỷ luật — Vé này) | Chênh lệch / Đánh giá |
|---|---|---|---|
| **Mô hình thực nghiệm** | `inclusionai/ling-3.1-flash:free` | `inclusionai/ling-3.1-flash:free` | Giữ nguyên điều kiện |
| **Cờ hợp đồng kỷ luật** | TẮT (Legacy Contract) | **BẬT (`1`)** | Biến thể duy nhất |
| **Tổng điểm đạt được** | **61.67 / 150** | 60.67 / 150 | Giảm nhẹ (-1.00đ) |
| **GPA trung bình** | **1.23 / 3.0** | 1.21 / 3.0 | Giảm nhẹ (-0.02) |
| **Số câu Provider Validated** | **2 / 50** (Q0689, Q0677) | **0 / 50** | **Không tăng (0/50)** |
| **Số câu Fallback trích cục bộ** | 46 / 50 | 48 / 50 | Tăng (+2 câu) |
| **Số câu Not Called (thiếu dữ liệu)** | 2 / 50 (Q0824, Q0668) | 2 / 50 (Q0824, Q0668) | 100% trùng khớp |
| **Số câu đạt tối đa (3.0)** | 4 câu | 4 câu | Ngang nhau |
| **Số câu đạt khá ($\ge$ 2.0)** | **7 câu** | 6 câu | Tương đương |
| **Độ trễ TB toàn câu** | 22.28s | 16.32s | Nhanh hơn (do rate-limit 14 câu) |
| **Độ trễ TB Provider Synthesis** | 11.54s | 7.04s | Nhanh hơn |
| **Lỗi kỹ thuật / Tiến trình** | **0 / 50 (0%)** | **0 / 50 (0%)** | Tuyệt đối an toàn |
| **Tổng số lượt gọi Provider** | 70 lượt | 36 lượt | 14 câu dính 429 từ Command Code |
| **Tỷ lệ dính `uncited_material_claim`** | 69 / 70 (98.6%) | **36 / 36 (100.0%)** | **Không cải thiện** |
| **Tỷ lệ dính `claim_budget_exceeded`** | 62 / 70 (88.6%) | **35 / 36 (97.2%)** | **Không cải thiện** |
| **Tỷ lệ dính `missing_limitations`** | 64 / 70 (91.4%) | **32 / 36 (88.9%)** | **Không cải thiện** |
| **Chi phí tiêu thụ** | **$0.00** | **$0.00** | Miễn phí 100% |
| **Tính toàn vẹn Index (Read-only)** | SHA256/MD5/Size khớp 100% | SHA256/MD5/Size khớp 100% | Không biến động 1 byte |

---

## 4. Phân tích chi tiết & Kết luận dứt khoát (Bước 4)

### 4.1. Giải phẫu hành vi: Tại sao hợp đồng khắt khe vẫn thất bại?
Trích xuất trực tiếp câu trả lời của `ling-3.1-flash:free` ở câu Q0708 (cả lần gọi đầu và lần repair) và câu Q0662:

- **Attempt 0 (Lần gọi đầu):**
  ```text
  The user asks in Japanese: "光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。"
  Translation: "If the optical path height exceeds 1.15 mm, does it always become unreadable by the camera?"
  Evidence:
  [1] Sirius 2 C7620: 光路高さが 1.24 以上の場合 Camera の読み込める範囲から外れ...
  ```
- **Attempt 1 (Lần tự sửa lỗi sau khi hợp đồng repair đã nhắc nhở xóa bỏ uncited opener):**
  ```text
  The user asks: "光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。" (Does exceeding optical path height 1.15 mm always cause camera read failure?)
  Evidence:
  [1][2][3] Sirius 2 C7620 report: 光路高さが 1.24 以上の場合 Camera の読み込める範囲から外れ...
  ```

**Kết luận thực nghiệm dứt khoát 100%:**
> **HỢP ĐỒNG KHÔNG PHẢI NÚT THẮT — NÚT THẮT LÀ TÍNH TUÂN THỦ (INSTRUCTION-FOLLOWING) CỦA BẢN THÂN MÔ HÌNH.**

Nhóm mô hình mã nguồn mở cỡ nhỏ/miễn phí (như Ling-3.1-Flash) sở hữu thiên hướng sinh ngữ (system bias/RLHF) được định hình rất mạnh: mô hình luôn có thói quen tự giải thích, dịch lại câu hỏi của người dùng và diễn giải trước khi trích dẫn dữ liệu. Việc bổ sung thêm chữ chỉ dẫn trong prompt (kể cả dùng các từ ngữ răn đe mạnh như *CRITICAL, NEVER, MANDATORY*) hoàn toàn bất lực trong việc thay đổi hành vi căn bản này ở cấp độ suy luận.

### 4.2. Quyết định kiến trúc & Hành động theo rào cứng:
1. **Lượt thử nghiệm KHÔNG THẮNG:** Tỷ lệ validated không tăng (0/50), GPA không cải thiện (1.21 vs 1.23), tỷ lệ lỗi kiểm định vẫn là 100% trên các lượt gọi thực tế.
2. **GIỮ NGUYÊN cờ cấu hình mặc định là TẮT:** `AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT=False`. Không bật mặc định cho production để tránh tăng thêm token rác trong context khi mô hình không lắng nghe.
3. **CẤM NỚI KIỂM ĐỊNH:** Giữ vững 100% các tiêu chí kiểm định nghiêm ngặt (`claim_budget`, `uncited_claim`, `critical_literal`, `missing_limitations`). Bộ kiểm định RAG v2 của WorkLens là chốt chặn bảo vệ sản phẩm chống ảo giác (zero hallucination).
4. **Vai trò sống còn của Deterministic Fallback:** Hệ thống Fallback trích cục bộ (`local_extractive_provider_fallback`) tiếp tục chứng minh là trụ cột kiến trúc hoàn hảo nhất: khi model miễn phí không đạt chuẩn kiểm định hoặc bị rate-limit, fallback tự động kích hoạt bảo toàn GPA ổn định 1.21–1.25, 0% lỗi kỹ thuật và đáp án luôn có trích dẫn tin cậy.

---

## 5. Bằng chứng cổng kiểm tra chất lượng (Quality Gates)

Toàn bộ các cổng chất lượng theo quy ước repo đều đạt chuẩn tuyệt đối tại commit hoàn tất:

1. **Biên dịch mã nguồn (`compileall`):**
   `uv run --no-sync --group dev python -m compileall src tests` -> **PASS (Exit Code 0)**.
2. **Kiểm thử Router & Synthesis Suite:**
   `uv run --no-sync --group dev pytest tests/test_ai_router.py tests/test_rag_v2_synthesis_provider.py tests/test_rag_v2_synthesis.py -q` -> **109/109 PASS (100%)**.
3. **Kiểm toán chất lượng (`cli audit`):**
   `uv run --no-sync --group dev python -m aios_habit.cli audit` -> **`{"errors": [], "status": "PASS", "warnings": []}`**.
4. **Kiểm tra khả năng nạp Workspace Chat App:**
   `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` -> **`IMPORT_OK`**.
5. **Kiểm băm toàn vẹn Index SQLite (Read-only Check):**
   - SHA-256 trước & sau: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` (Khớp 100%).
   - MD5 trước & sau: `239009676829484049738866329de9f2` (Khớp 100%).
   - Dung lượng: `2,942,201,856` bytes (Khớp 100%).
