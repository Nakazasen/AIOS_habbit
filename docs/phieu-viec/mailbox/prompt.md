# Ticket E1 — Điều tra khâu "viết câu trả lời" làm rớt dữ kiện (chỉ đọc, không sửa code)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- D3 (`fc024d2`, ĐẠT): kho đã đủ — B1/B3 có đáp án trong evidence truy xuất được,
  nhưng câu trả lời cuối KHÔNG nêu ra. B5: evidence truy xuất về thiếu định nghĩa
  `HOUSE_METHOD` (lỗi ở khâu tìm/xếp hạng, không phải khâu viết).
- Chi tiết trong `docs/phieu-viec/ket-qua/FIX3_baseline-D3-onnx.md` (bảng dòng 15–22,
  phân tích dòng 30–33).
- Chế độ tự lái toàn phần (user 2026-09-26): tự quyết, không hỏi; có lỗi thì điều tra
  tiếp trong repo.

## Việc cần làm (TẤT CẢ chỉ đọc — không sửa code, không ghi index)

1. Chạy lại B1 và B3 (read-only: `index_read_only=True`, `ensure_embeddings_on_open=False`,
   `BGE_BACKEND=onnx`, 2 flag summary bật như D3), log đầy đủ:
   - evidence/chunk truy xuất được (id + text),
   - prompt gửi vào khâu viết câu trả lời cuối (đầy đủ, không cắt),
   - câu trả lời cuối.
2. Mổ xẻ vì sao dữ kiện có trong evidence lại rớt khỏi câu trả lời:
   - Prompt có yêu cầu trích dữ kiện không, hay chỉ bảo "tóm tắt"?
   - Evidence có bị cắt bớt (truncate) trước khi đưa vào prompt không?
   - Có tầng lọc/rerank nào sau retrieval làm mất chunk chứa đáp án không?
   - Dữ kiện nằm ở vị trí nào trong evidence (đầu/cuối/giữa) — có mẫu hình không?
3. Với B5: evidence thiếu định nghĩa `HOUSE_METHOD` — do chunking cắt mất,
   do lexical/rerank không đưa chunk đúng lên, hay chunk đáp án không tồn tại?
   (D2 đã xác nhận đáp án B5 có trong file đã ingest.)
4. Đề xuất fix CỤ THỂ cho từng ca (sửa prompt? sửa thứ tự evidence? sửa chunking?),
   kèm file/hàm cần đụng. Không cần viết code trong ticket này.

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
  (hostname, SHA code lúc chạy, log evidence/prompt/answer của B1+B3, kết luận
  nguyên nhân từng ca, đề xuất fix cụ thể).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG**.
