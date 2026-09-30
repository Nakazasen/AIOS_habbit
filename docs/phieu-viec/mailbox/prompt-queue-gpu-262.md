# Vé GPU-262 — Nhúng GPU 52.979 chunk (262 nguồn LSU) + đóng gói delta cho PC0575

## Lệnh ưu tiên (user trực tiếp, tối 30/09/2026)
Vé này là ưu tiên số 1 tối nay. Nếu bạn đang ở giữa một bước ghi atomic của vé LSU-1:
hoàn tất bước đó (tối đa 15 phút), ghi mốc, rồi chuyển sang vé này ngay.
Nếu LSU-1 còn đang khảo sát (chỉ đọc, chưa ghi gì): chuyển ngay, không cần chờ.

## Bối cảnh
- PC0575 đã xuất xong `scratch/export_262/text_export.jsonl`: 262 `document_id` →
  52.979 chunk, 81.531.448 byte, SHA-256
  `95aecf07297bfdf2e4f7462fd477fa052a89aa3eaaa462c53cbce40d341bb505`,
  0 text rỗng. Export dùng đúng `content_text` + registry + chunker hiện tại của app —
  text là chuẩn tuyệt đối, KHÔNG trích xuất lại từ nguồn.
- 5 document (nhóm A) đã có trong production PC0575 (verify khớp 100%);
  257 document (nhóm B) còn thiếu. Chi tiết nhóm xem báo cáo
  `docs/phieu-viec/ket-qua/hodap-lsu-loi.md` (mốc 7/8).
- File đã có trên Drive (user upload thay USB):
  https://drive.google.com/file/d/1zO2KO4RkFsjE4UBahTCHJg6TkDHRjUNb/view?usp=sharing
- Production PC0575
  (`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`)
  — vé này KHÔNG ĐỤNG tới. Chỉ nhúng vào staging trên máy nhà; merge về PC0575
  là vé khác (Muse ra sau khi review độc lập).

## Việc cần làm
1. Tải file từ Drive về ổ C (vd `C:\tmp\gpu-262\text_export.jsonl`).
   CẤM ghi ổ D (ổ D hỏng vật lý, cấm vĩnh viễn).
   Verify: size đúng 81.531.448 byte; SHA-256 đúng
   `95aecf07297bfdf2e4f7462fd477fa052a89aa3eaaa462c53cbce40d341bb505`.
   Lệch → DỪNG, đặt mailbox `cho-muse`, ghi rõ số đo thực tế.
2. Tạo index staging MỚI trên ổ C (vd `C:\AIOS_staging_262\library.sqlite`),
   schema y hệt collection `tri_thuc` hiện tại.
   KHÔNG dùng file canary `C:\AIOS_habit_index_ve03\library.sqlite`
   (sắp xóa theo vé don-canary), KHÔNG ghi production
   `C:\AIOS_p1_4\tri_thuc\library.sqlite`.
3. Nhúng GPU toàn bộ 52.979 chunk: tái dùng tooling Vé 0.3; đối chiếu TRƯỚC khi chạy —
   model BGE-M3 đúng rev `5617a9f`, onnxruntime==1.28.0, checksum cây onnx
   `728c9eb7…`. Backend tự chọn CUDA (fail-closed nếu thiếu model).
   Ghi thời gian bắt đầu/kết thúc, tốc độ chunk/giây.
4. Verify sau nhúng (chỉ đọc, không sửa):
   - Đủ 262/262 `document_id`; đếm chunk retrievable.
   - Fingerprint quét lại phải `016c5255…` (ghim cả onnxruntime).
   - Spot-check 20 chunk: cosine(GPU, CPU) ≥ 0.999.
5. Đóng gói delta cho PC0575: xuất toàn bộ dòng `chunks` + `chunk_embeddings`
   của 262 `document_id` ra `C:\AIOS_staging_262\delta_262.sqlite`
   (kèm `manifest.json`: SHA-256 file delta, số document, số chunk, fingerprint).
   Merge về PC0575 sẽ skip `document_id` đã tồn tại → nhúng thừa nhóm A cũng an toàn.
6. Báo cáo `docs/phieu-viec/ket-qua/gpu-262.md`: SHA/size file nguồn, thời gian nhúng,
   số ID/chunk, fingerprint, SHA delta, đường dẫn delta.
   Commit riêng từng bước trên branch `phieu-viec/rag-fix1`, không merge `main`.
   Xong → mailbox `xong-cho-duyet`.

## Cấm
Không ghi production, không ghi ổ D, không re-embed CPU, không merge `main`,
không xóa staging/delta khi chưa có vé merge.

## Tiêu chí ĐẠT (Muse review độc lập)
Đủ 262 ID, fingerprint `016c5255…`, delta đầy đủ + manifest khớp, báo cáo có số đo
từng chặng.
