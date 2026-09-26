# Ticket G1 — Kiểm kê + ingest dữ liệu LSU và case lỗi (theo mẫu D2)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Chuỗi E đã xong (E1 điều tra, E2 fix synthesis ĐẠT, E3 dọn XML extractor ĐẠT,
  E4 default ONNX fp32 ĐẠT — Muse review 2026-09-27): index hiện tại 74
  document / ~1064 chunk retrievable, fingerprint ONNX `016c5255…` / PyTorch
  `ce7fb53f…`, pending 0, extractor dọn XML sau flag
  `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` (mặc định tắt).
- Dữ liệu cần ingest nằm sẵn LOCAL trên máy nhà, OMP đọc trực tiếp, KHÔNG tải Drive:
  `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy` — gồm dữ liệu LSU
  (log JIG, thử nghiệm 6pcs/TAPE MIRROR, self-diagnosis, pptx đào tạo LSU) và
  case điều tra lỗi (`Loi KDTPS.xlsx`, `Bang ma loi/`, `SƠ đồ điện/`,
  UWCA FXXX / SCT error-code xls...).
- Chế độ tự lái toàn phần (user 2026-09-26): tự quyết mọi quyết định kỹ thuật,
  không hỏi; sai thì revert commit và viết ticket sửa.

## Việc cần làm

1. **Kiểm kê local**: đếm file trong `Tài liệu của tất cả dòng máy` theo loại
   (pdf/xlsx/xls/pptx/ppt/doc/msg/csv...), ghi dung lượng, đối chiếu với index
   hiện tại → liệt kê file CHƯA có trong index và file ĐÃ có.
2. **Kiểm tra extractor**: pptx/ppt/msg có được extractor đọc không; nếu không,
   báo rõ loại nào bị bỏ qua + lý do. KHÔNG tự viết extractor mới trong ticket này.
3. **Ingest file mới theo đúng quy trình D2**: dry-run trước → backup mới
   (file sibling, `integrity_check=ok`, fail-closed nếu backup lỗi) → apply theo
   batch có resume → verify cuối (số doc/chunk/retrievable/pending, fingerprint
   ONNX/PyTorch, `integrity_check`, kích thước file index trước/sau).
4. Ingest SAU E3/E4: chunk được dọn XML ngay từ extractor (flag
   `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` dùng đúng cách E3 đã nghiệm thu),
   embed bằng backend ONNX fp32 (default sau E4). KHÔNG re-embed hàng loạt vector
   cũ: kiểm tra pending theo fingerprint trước và sau, số liệu phải khớp logic.
5. Mọi apply đều dry-run trước + backup mới + batch/resume; thiếu một trong ba
   thì DỪNG và báo rõ số liệu.

## Điều cấm

- KHÔNG merge vào `main`. KHÔNG `--apply` khi chưa có backup mới integrity ok.
- KHÔNG bật/tắt các flag khác (drain flag giữ tắt như cũ).
- KHÔNG ingest file không xác định được nguồn → ghi vào danh sách bỏ qua kèm lý do.

## Nghiệm thu

- Số liệu trước/sau rõ ràng: +bao nhiêu doc/chunk/retrievable, pending 0,
  `integrity_check=ok` trước/sau, kích thước index trước/sau giữ nguyên logic.
- Báo cáo liệt kê: file đã ingest (nguồn/sheet/dòng) + file bị bỏ qua kèm lý do
  (loại file extractor không hỗ trợ, trùng, không xác định nguồn...).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/BUOC0_ingest-G1-lsu-case-loi.md`
  (hostname, SHA code lúc chạy, số liệu kiểm kê, số liệu ingest trước/sau,
  danh sách bỏ qua kèm lý do, verify integrity).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG**.
