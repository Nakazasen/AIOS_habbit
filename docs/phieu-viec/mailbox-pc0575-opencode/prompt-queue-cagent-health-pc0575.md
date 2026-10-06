# Vé CAGENT-HEALTH-PC0575 — Kiểm tra sức khỏe endpoint C-Agent trước vé WIRE

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Thợ:** opencode.
**Role gợi ý:** SMOL (kiểm tra nhanh).

## Bối cảnh

- Vé `WIRE-QA-CAGENT-PC0575` sắp tới sẽ đẩy 3.392 cặp hỏi-đáp qua lane C-Agent.
- Lần đo gần nhất (05/10): endpoint C-Agent sống, phản hồi 30,76 giây cho 1 câu.
- Vé này: kiểm tra nhanh endpoint còn sống không, độ trễ hiện tại bao nhiêu,
  để vé WIRE không đâm đầu vào endpoint chết.

## Endpoint

- `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`
- Module gọi: `src/aios_habit/cagent_api.py`, hàm `call_cagent_prediction`.
- Tuyệt đối không hardcode URL mới, không bịa endpoint.

## Việc cần làm (đúng thứ tự)

1. Gọi 3 câu hỏi mẫu qua `call_cagent_prediction` (lấy từ `wire-qa-mapping.jsonl`,
   1 câu mỗi nhóm MOM/LSU/Điều-tra-lỗi). Đo thời gian phản hồi từng câu.
2. Ghi nhận: endpoint SỐNG/CHẾT, độ trễ từng câu (giây), có lỗi gì không.
3. Nếu CHẾT hoặc trễ >120 giây/câu: chẩn đoán nguyên nhân ở mức có thể
   (mạng, endpoint, key) và báo rõ — KHÔNG tự sửa hạ tầng ngoài phạm vi vé.
4. Báo cáo ngắn `docs/phieu-viec/ket-qua/cagent-health-pc0575.md`:
   trạng thái, 3 số đo, kết luận SẴN SÀNG / CHƯA SẴN SÀNG cho vé WIRE.

## Rào cứng

- Chỉ đọc/kiểm tra, không sửa code lane C-Agent trừ khi vé yêu cầu.
- Không merge `main`. Python 3.11.

**Verdict:** Muse review trên bằng chứng độc lập.
