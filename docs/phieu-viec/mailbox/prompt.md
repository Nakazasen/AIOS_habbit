# Ticket D3 — Baseline B1–B5 (+H3) trên corpus đầy đủ, worker ONNX fp32 (chỉ đọc)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- D2 (`20bce54`, ĐẠT, Muse review 2026-09-26): index thật máy `h410asrock`
  đã đầy đủ — **74 document / 1.272 chunk / 1.064 retrievable**, pending vector
  = 0, dense/sparse ONNX fp32 `016c5255…` × 1.064 (PyTorch cũ giữ × 340),
  `integrity_check` live ok.
- Chuỗi đáp án B1/B2/B3/B5 đã có trong index (D1 xác nhận qua grep);
  B4 vẫn không có mã ví dụ trong bất kỳ nguồn nào → **B4 loại trừ khỏi
  đánh giá đúng/sai** (ground truth lệch với tài liệu hiện có, đã xác nhận).
- Mục tiêu D3: đo baseline đầy đủ trên corpus sau ingest — mỗi câu chạy với
  worker ONNX fp32, so đáp án với ground truth và so latency với baseline
  PyTorch (báo cáo commit `484ac76`).

## Việc cần làm

1. `git pull origin phieu-viec/rag-fix1`. Đọc báo cáo D2
   (`docs/phieu-viec/ket-qua/FIX3_ingest-D2-apply.md`) để lấy đúng đường dẫn
   index thật trên máy này.
2. Chạy worker với `BGE_BACKEND=onnx` (backend ONNX fp32 đã migrate xong ở
   Bước B + D2). Worker init phải < 300 s (lần đo Bước C: 3,94 s).
   Nếu init treo/quá 300 s → DỪNG ngay, báo hiện tượng, không chạy tiếp.
3. Chạy lại đúng bộ câu hỏi **B1, B2, B3, B4, B5, H3** với bộ đáp án tham chiếu
   đã dùng ở baseline PyTorch (`484ac76`) — không đổi câu hỏi, không đổi
   ground truth.
4. Với mỗi câu ghi: mode (overview/focused/full/hybrid), latency worker,
   có abstain/timeout không, các fact trong đáp án so với ground truth
   (đủ/thiếu/sai ở điểm nào). B4 vẫn chạy nhưng không tính đúng/sai.
5. Ghi nhận nhiễu XML nếu thấy (ví dụ B3 từng lẫn `xmlns` slide) — chỉ ghi
   nhận, KHÔNG dọn trong ticket này.
6. **Chỉ đọc**: không ghi thêm vector, không ingest, không `--apply` bất cứ
   thứ gì vào index. (Query không được làm đổi số liệu verify của D2.)

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_baseline-D3-onnx.md`
  (hostname, SHA, bảng từng câu: mode, latency, so đáp án với ground truth,
  chênh lệch latency so với baseline PyTorch `484ac76`, nhận xét nhiễu XML).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `docs/phieu-viec/mailbox/trang-thai.md` → `xong-cho-duyet`
  (ghi commit SHA + đường dẫn báo cáo), rồi **DỪNG**.
