# Ticket D1 — Điều tra vì sao chỉ 25/108 document được index + dry-run ingest (CHỈ ĐỌC, không ghi)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Điều tra `b90a94a`: index canary `tri_thuc` có 25 document / 413 chunk (340 vector);
  `materialized_sources` có 108 file, **83 file không có path trong index**.
- Hệ quả: B1/B2/B3/B5 thiếu chunk chứa đáp án → trả lời sai toàn bộ trên cả
  PyTorch (`484ac76`) lẫn ONNX (`cc12d67`, Bước C — ĐẠT).
- Mục tiêu D1: trả lời "83 file đi đâu" + dry-run kế hoạch ingest.
  **Ticket này TUYỆT ĐỐI chỉ đọc — không ghi index, không ingest thật.**

## Phạm vi

- Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (máy `h410asrock`). Mở sqlite ở chế độ **read-only** (`mode=ro`).
- Không chạy `--apply`, không ingest thật, không sửa file index dưới mọi hình thức.

## Việc cần làm

1. Liệt kê 108 file trong `materialized_sources`; đối chiếu với `documents`
   trong index → bảng 108 dòng, mỗi dòng: `indexed` / `missing`.
2. Với 83 file missing, phân loại nguyên nhân theo nhóm (không cần từng file
   nếu cùng một nguyên nhân):
   - Có manifest/allowlist nào giới hạn ingest chỉ 25 document không?
   - Có bị filter loại không (định dạng, dung lượng, ngày tháng, cổng
     `usable_elements`, ...)? Ghi rõ điều kiện filter nào đã loại chúng.
   - Ingest đã từng thử và fail? (tìm log / error message)
   - Hay chưa bao giờ được đưa vào pipeline?
3. Kiểm tra trong 83 file missing có chứa chuỗi đáp án B1–B5 không
   (grep trực tiếp trên file, không qua index):
   `11922`, `12860`, `12626`, `YY2-Z151`, `YY2-Z152`, `nvarchar(4000)`,
   `HOUSE_METHOD`, `Y302YL93020100`.
   → Kết luận: ingest 83 file có kỳ vọng sửa được B1/B2/B3/B5 không?
4. Dry-run ingest 83 file (**không ghi**): ước tính số document/chunk sẽ thêm,
   liệt kê cảnh báo (file lỗi, XML noise, trùng lặp với 25 document cũ...).
5. Ghi chú: **KHÔNG dọn XML** trong ticket này — dọn sau khi có baseline B
   trên corpus đầy đủ (theo thứ tự đã chốt).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_ingest-D1-dieu-tra.md`
  (ghi hostname, commit SHA, đầy đủ số liệu 108/83, kết quả grep B1–B5).
- Commit **riêng** + push branch `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG chờ duyệt** — quyết định ingest apply thật là việc của ticket D2,
  sau khi user duyệt (ghi index thật cần dry-run + backup + duyệt rõ ràng).
