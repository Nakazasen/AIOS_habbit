# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: E3 — dọn XML thô ở extractor (code + test, không ghi index)
- Ticket trước: E2 — ĐẠT (commit `a83f8ff4`, Muse review 2026-09-26)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Ghi chú: Muse review E2 ĐẠT: fix claim budget + giảm summary chen đầu + exact-identifier rescue đã vào code riêng (diff index.py +95/-5, pipeline.py +7/-1, synthesis.py +306/-25, test +180), B1/B2/B3/B5 read-only ONNX đúng (B2 không gắn rõ ACR — đã ghi nhận trung thực, không tính đạt), index không đổi 29.851.648 byte trước/sau, không ingest/--apply; pytest 79/79 RAG, full suite 3.132 đạt/2 bỏ qua/21 lỗi đều ngoài diff. OMP `git pull` rồi đọc `prompt.md` làm E3.
- Cập nhật lần cuối: 2026-09-26 (Muse)
