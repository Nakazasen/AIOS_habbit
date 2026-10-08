# VÉ: SYNTH-CONTRACT-FREE-HOME (thử hợp đồng tổng hợp khắt khe cho model free — mở khoá validated mà không nới kiểm định)

- Mã vé: `SYNTH-CONTRACT-FREE-HOME`
- Role gợi ý: DEFAULT (code hợp đồng + đo thực nghiệm)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-contract-free-home.md`
- Căn cứ: vé `SYNTH-MODEL-AB-HOME` (báo cáo `synth-model-ab-home.md` §3–§4): cả 3 model free đứng một mình chỉ đạt validated 0–2/50 (Gemini cũ 9/50); lỗi kiểm định chủ đạo là `uncited` + `claim_budget` — model free viết dòng diễn giải không trích dẫn và vượt số dòng cho phép. Giả thuyết của vé này: hợp đồng (contract prompt) hiện tại chưa ép đủ kỷ luật "mỗi dòng là một dữ kiện có trích dẫn" cho phong cách của nhóm model này.

## Việc phải làm

1. Đọc lại hợp đồng hiện tại (`format_provider_synthesis_contract` trong `src/aios_habit/rag_v2/synthesis.py`, gồm phần `budget_rule` đã thêm ở vé CLAIM-BUDGET) + thống kê từ rows của vé A/B: tỉ lệ lượt gọi dính `uncited` / `budget` / `missing_citations` theo từng model.
2. Thiết kế biến thể hợp đồng "kỷ luật trích dẫn" cho tuyến provider (chỉ thay ĐỢT chữ hướng dẫn, ví dụ: mỗi dòng factual PHẢI kết thúc bằng trích dẫn `[n]`; cấm mọi dòng mở đầu/kết luận không trích dẫn; số dòng tối đa = ngân sách, ghi số cụ thể; ưu tiên ít dòng chắc chắn hơn nhiều dòng). Giữ biến thể sau cờ cấu hình để bật/tắt được (mặc định TẮT cho tới khi có verdict nhận).
3. Thực nghiệm trên đúng bộ 50 câu + điều kiện của vé A/B (CPU-only, index chỉ đọc, đếm theo `che_do` từ rows, reset health mỗi câu), model chính `ling-3.1-flash:free` (con tốt nhất ở A/B):
   - Lượt đối chứng: hợp đồng hiện tại (số đã có ở Lượt A của A/B — chạy lại nếu cần tính đồng thời).
   - Lượt thử: hợp đồng kỷ luật trích dẫn.
   So: validated, GPA, fallback, lỗi uncited/budget theo lượt gọi, độ trễ.
4. Nếu lượt thử thắng rõ (validated tăng có ý nghĩa, GPA không giảm): đề xuất bật mặc định cho tuyến pool free trong báo cáo (điều phối duyệt mới đổi mặc định). Nếu không thắng: kết luận thẳng "hợp đồng không phải nút thắt — nút thắt là tuân thủ của model" và dừng, không nới kiểm định.

## Rào cứng

- CẤM nới kiểm định: không tăng `max_claims`, không đổi cách đếm, không tắt/bớt bất kỳ lỗi kiểm định nào, không đổi rubric. Chỉ được thay chữ hợp đồng hướng dẫn + cờ bật/tắt.
- Test hồi quy: test hợp đồng hiện có phải xanh; thêm test cho biến thể (hợp đồng chứa đủ các chỉ dẫn kỷ luật; cờ tắt = hành vi cũ nguyên vẹn).
- Không ghi index (kiểm băm trước/sau), không merge `main`; đo bằng model free ($0 credits).
