# Ticket XẾP HÀNG: E3 — Dọn XML thô ở extractor (code + test, không ghi index)

## Bối cảnh
Chuỗi E hoàn thiện trả lời. E3 dọn XML thô còn sót ở tầng extractor.

## Việc cần làm
1. Rà soát `src/aios_habit/document_extractors.py`, `src/aios_habit/excel_extractors.py`,
   `src/aios_habit/deep_document_parsers.py`: tìm chỗ còn lọt tag XML thô vào text trích xuất.
2. Viết hàm dọn XML (strip tag, giữ nội dung text) + test unit:
   - Test với XML lồng nhau, CDATA, entity (`&amp;`, `&lt;`...).
   - Test "vất lại file cũ thì bỏ qua" (theo luật vé code).
3. Chạy full test liên quan, tất cả pass.

## Cấm
- Không ghi index, không embed. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/e3-don-xml-extractor.md`: mô tả fix + số test pass/fail.
Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
