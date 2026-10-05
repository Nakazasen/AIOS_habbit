# VÉ: BENCHMARK-LOCAL-MODELS-PC0575 (đo model chấm điểm + model mini trên đúng máy công ty)

- Mã vé: `BENCHMARK-LOCAL-MODELS-PC0575`
- Role OMP gợi ý: DEFAULT (tải model + đo nhiều chỉ số)
- Máy: KDTVN-PC0575 (bắt buộc đo trên máy đích — i5, 16GB, không GPU)
- Báo cáo: `docs/phieu-viec/ket-qua/benchmark-local-models-pc0575.md`

## Bối cảnh

Đường AI cloud (cầu Gemini Web + Nakazasen Router) chết từ 02/10, chưa rõ ngày hồi.
User chốt hướng dự phòng bằng model local (thảo luận 05/10). Vé này ĐO THẬT trên
máy công ty trước khi quyết định đưa vào đâu — không đoán mò.

## Việc cần làm

**Đối tượng 1 — model chấm điểm (không sinh chữ): bge-reranker (cross-encoder)**
1. Tải bge-reranker về máy (~1GB).
2. Đo trên mẫu câu hỏi thật (lấy từ log/hỏi đáp có sẵn):
   - Thời gian chấm điểm + xếp hạng lại mỗi câu (ms/câu) trên CPU.
   - Độ trúng cải thiện so với xếp hạng hiện tại (đánh giá tay trên mẫu).
   - RAM đỉnh khi chạy.

**Đối tượng 2 — model mini viết câu ngắn (sinh chữ thật)**
1. Thử nhanh 3 con: MiniCPM5-1B, Llama-3.2-1B, Qwen2.5-1.5B (bản lượng tử Q4).
   Chọn 1 con viết tiếng Việt ổn nhất để đo kỹ.
2. Đo trên con đã chọn:
   - Tốc độ sinh chữ (token/giây) trên CPU, với câu tóm tắt ngắn 2-3 câu từ chunk cho sẵn.
   - Chất lượng tóm tắt tiếng Việt (đánh giá tay vài mẫu: có đúng ý chunk không, có bịa không).
   - RAM đỉnh khi chạy, dung lượng đĩa từng con.

**Đo pipeline tuần tự** (đúng cách chạy thật — không chạy song song):
embed query → rerank → sinh tóm tắt. Ghi RAM đỉnh cả pipeline, tổng thời gian mỗi câu.

## Tiêu chí nghiệm thu

- Báo cáo có đủ số: ms/câu (rerank), token/giây (LLM), RAM đỉnh từng bước + cả pipeline,
  GB đĩa, độ chính xác trên mẫu, nhận xét chất lượng tóm tắt.
- Kết luận rõ: có nên đưa vào không; nếu có thì đưa vào chỗ nào
  (rerank tìm kiếm / định tuyến lane / tóm tắt khi cloud chết); chọn con LLM nào và vì sao.
- Verdict ĐẠT = đo đủ chỉ số trên, số liệu thật từ máy PC0575, kết luận dựa trên số.
- Không sửa code app (vé benchmark độc lập). Không merge `main`.
