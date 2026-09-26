# Ticket E3 — Dọn XML thô ở extractor (code + test, không ghi index)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- E2 (`a83f8ff4`, ĐẠT — Muse review 2026-09-26): khâu tổng hợp đã fix claim budget +
  ưu tiên chunk thân + thu hồi exact identifier; B1/B2/B3/B5 read-only ONNX đúng.
- Điều tra D1/B-sai (đã có trong báo cáo E1): index canary có 33 chunk chứa `xmlns`,
  23 chunk chứa `<p:sld>` — XML thô lọt vào chunk từ tầng extractor, làm bẩn corpus
  (đã thấy lẫn XML trong kết quả B3 ở vòng trước). Đây là item thứ 3 trong thứ tự
  ưu tiên user chốt (sau: diagnostic ONNX timeout ✓, ingest 83 file + chạy lại B ✓).
- Chế độ tự lái toàn phần (user 2026-09-26): tự quyết mọi quyết định kỹ thuật, không hỏi;
  sai thì revert commit và viết ticket sửa.

## Việc cần làm

1. **Xác định điểm rò rỉ**: tìm tầng extractor hiện tại (chỗ materialized_sources /
   chunking chuyển PPTX/DOCX/PDF/XML thành text chunk): XML thô (namespace, thẻ,
   thuộc tính, comment, `p:sld`...) lọt vào text ở đâu.
2. **Dọn XML ở tầng extractor**: strip markup, giữ text thuần và DỮ KIỆN
   (mã, số, kiểu dữ liệu, giá trị) không mất, không biến dạng. Nếu đổi hành vi
   extractor → mọi code mới nằm sau **feature flag mặc định TẮT** (quy tắc bất biến).
3. **Test**: unit test với sample input có XML (xmlns, p:sld, namespace, comment) →
   chunk sạch XML, dữ kiện còn nguyên; regression test đảm bảo file sạch XML vẫn
   chunk y hệt như cũ. Chạy pytest liên quan + `compileall`; full suite nếu chạm lõi.
4. **Đo before/after** trên index canary hoặc sample đủ đại diện: số chunk chứa
   `xmlns`/`<p:sld>`/thẻ XML phải về 0; không làm hại retrieval (không giảm recall
   lexical trên sample có đáp án đã biết).
5. Ticket này **KHÔNG ghi index thật** (không ingest, không --apply, không backfill
   index production). Nếu thấy cần migrate index hiện tại → DỪNG ở phạm vi code +
   test, chỉ ghi đề xuất vào báo cáo (đề xuất phải kèm dry-run trước + backup trước
   nếu sau này làm).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
  (hostname, SHA code lúc chạy, vị trí extractor sửa, diff chính, kết quả test,
  số chunk nhiễu XML before/after, bàn giao test case).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG**.
