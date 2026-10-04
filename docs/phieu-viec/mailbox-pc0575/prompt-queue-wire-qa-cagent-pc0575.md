# Vé WIRE-QA-CAGENT-PC0575 — Nối dữ liệu hỏi đáp vào giao diện máy công ty để hỏi đáp qua C-Agent

**Mức ưu tiên:** cao (user cần demo cho sếp trong hôm nay).
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `SPEED-COLDSTART-PC0575`, trước `KNOWLEDGE-ENRICH-PILOT`.

## Bối cảnh

- 3.393 cặp hỏi đáp ChatGPT đã hoàn tất đêm 4→5/10: MOM 608 + LSU 1.790 + Điều-tra-lỗi 995 (Q1–Q3406). Nằm trên GitHub nhánh `phieu-viec/rag-fix1`: `docs/phieu-viec/chatgpt-enrichment-raw/` (toàn bộ) + `docs/phieu-viec/chatgpt-enrichment-fixed/` (MOM+LSU+Điều-tra-lỗi batch-55..87 đã audit).
- Lane C-Agent đã đo thành công 6/6 câu ngày 2/10 trên chính máy này (16,5–45,8 s/câu) — đây là đường AI sống ở công ty (2 đường ở nhà đã chết).
- User cần: hỏi đáp được trên giao diện máy công ty từ dữ liệu này, trong hôm nay.

## Yêu cầu

1. `git pull origin phieu-viec/rag-fix1`; kiểm đếm đủ 3.393 cặp (Q1–Q3406 liên tục, trừ Q639–Q648 và Q3206–Q3208 bỏ có chủ đích đã ghi trong manifest).
2. Kiểm tra lane C-Agent còn sống: hỏi 1 câu đơn giản qua UI, ghi thời gian. Nếu chết → DỪNG, báo đúng điểm kẹt (mạng/endpoint/hạn mức), không bịa.
3. Nối dữ liệu hỏi đáp vào giao diện chat để user hỏi đáp được qua C-Agent. Cách làm worker tự chọn cho gọn (gợi ý: mở rộng cơ chế đọc file bản thảo trực tiếp như `answer_draft_fallback.py`, hoặc lookup theo cặp). Rào cứng: mọi câu trả lời từ dữ liệu này phải hiện nhãn `Bản thảo — chưa qua chuyên gia duyệt`; không nhập vào index production; không ghi DB.
4. Demo 3 câu mẫu qua UI, ghi thời gian từng câu: (a) tra mã lỗi C0980, (b) 1 câu hỏi đáp chung, (c) 1 câu lấy từ cặp Q&A có sẵn.

## Điều kiện nghiệm thu

- Hỏi từ UI → ra câu trả lời dựa trên cặp Q&A, có nhãn bản thảo đúng mẫu.
- Thời gian mỗi câu < 60 giây (theo biên C-Agent đã đo).
- Index production không đổi (đo SHA trước/sau).

**Verdict:** Muse review trên bằng chứng độc lập (log demo 3 câu + diff code).
