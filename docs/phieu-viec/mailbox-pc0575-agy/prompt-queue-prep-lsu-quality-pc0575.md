# Vé PREP-LSU-QUALITY-PC0575 — Chuẩn bị bộ câu hỏi đo chất lượng LSU

**Máy thực hiện:** [CTY] KDTVN-PC0575 (thợ agy).
**Role gợi ý:** SMOL (chẩn đoán + soạn bộ câu hỏi, không code nặng).

## Bối cảnh

Vé `LSU-QUALITY-PC0575` (thợ OMP) sẽ đo chất lượng trả lời LSU trên câu hỏi thật.
Vé này chuẩn bị trước bộ câu hỏi + rubric để OMP chỉ việc chạy đo.

## Việc cần làm

1. Đọc `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl`, lọc các cặp `category=LSU`
   (kỳ vọng 1.790 cặp — đếm thực tế, không hardcode).
2. Chọn 50 câu đại diện, phủ các nhóm: mã lỗi / nguyên nhân / đối sách / thông số kỹ thuật.
3. Viết rubric chấm điểm thang 0–3:
   0 = sai trọng tâm; 1 = gần đúng nhưng thiếu ý chính;
   2 = đúng; 3 = đúng + có trích dẫn nguồn.
4. Lưu `docs/phieu-viec/ket-qua/lsu-quality-set.md`: bảng 50 câu (id, câu hỏi,
   đáp án tham chiếu, nhóm) + rubric. Ghi rõ nhãn "bản thảo — chưa qua chuyên gia duyệt".

## Rào cứng

- Chỉ đọc JSONL, không sửa. Không merge `main`.
- Không tự bịa câu hỏi ngoài JSONL.
