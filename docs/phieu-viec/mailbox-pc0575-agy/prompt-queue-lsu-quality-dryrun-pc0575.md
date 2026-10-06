# Vé LSU-QUALITY-DRYRUN-PC0575 — Chạy thử pipeline đo chất lượng LSU trên index TẠM

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Thợ:** agy.
**Role gợi ý:** SMOL (chạy thử, không đo thật).

## Bối cảnh

- agy đã xong bộ 50 câu hỏi (`docs/phieu-viec/ket-qua/lsu-quality-set.md`, verdict ĐẠT).
- opencode đã xong khung đo (`src/aios_habit/quality_harness.py`, verdict ĐẠT).
- Vé đo thật `LSU-QUALITY-PC0575` phải chờ index chính được khôi phục
  (vé `RESTORE-INDEX-SPLIT-PC0575` đang chạy) + vé `WIRE-QA-CAGENT-PC0575` nối xong.
- Vé này: chạy thử TRỌN PIPELINE đo lường trên index TẠM hiện tại để bắt lỗi
  tích hợp sớm (câu hỏi load đúng không, harness chạy 2 lane có lỗi không,
  rubric chấm có vận hành không, báo cáo sinh ra đúng không).

## Rào cứng

- Đây là DRY-RUN trên index TẠM `062ec090` (đã biết lệch nguồn LSU 0/494) —
  ĐIỂM SỐ KHÔNG CÓ GIÁ TRỊ ĐO THẬT. Mọi báo cáo/output phải ghi rõ nhãn
  "DRY-RUN trên index TẠM — không phải kết quả đo thật".
- Không nhập điểm dry-run vào kho tri thức. Không merge `main`. Python 3.11.
- Heartbeat mốc tiến độ 15 phút/lần (vé chạy đo có thể lâu).

## Việc cần làm (đúng thứ tự)

1. Load bộ 50 câu từ `docs/phieu-viec/ket-qua/lsu-quality-set.md`.
2. Chạy khung `src/aios_habit/quality_harness.py` trên cả 2 lane:
   lane C-Agent và lane RAG (index TẠM). Mỗi câu chấm theo rubric 0–3 trong báo cáo.
   Nếu lane nào lỗi kỹ thuật (không phải do đáp án dở): ghi rõ lỗi, không chấm bừa.
3. Sinh báo cáo thử `docs/phieu-viec/ket-qua/lsu-quality-dryrun-pc0575.md`:
   - Tỉ lệ câu chạy thành công từng lane (không phải tỉ lệ đạt điểm).
   - Danh sách lỗi kỹ thuật gặp phải (timeout, parse, lane sập...) + cách khắc phục đề xuất.
   - 5 câu ví dụ có đáp án + điểm chấm thử để minh họa rubric vận hành được.
   - Kết luận: pipeline SẴN SÀNG / CHƯA SẴN SÀNG cho lần đo thật.

## Điều kiện nghiệm thu

- 50/50 câu được đưa qua pipeline (kể cả câu lỗi kỹ thuật — phải ghi rõ).
- Báo cáo dry-run có đủ 4 mục trên, nhãn DRY-RUN rõ ràng.
- Commit riêng nhánh `phieu-viec/rag-fix1`.

**Verdict:** Muse review trên bằng chứng độc lập.
