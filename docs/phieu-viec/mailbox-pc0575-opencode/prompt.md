# VÉ: SRC-SYNC-PC0575 (đưa file nguồn về máy công ty để RAG chạy đúng thiết kế strict_semantic)

- Mã vé: `SRC-SYNC-PC0575`
- Role OMP gợi ý: DEFAULT (điều tra đường dẫn/dữ liệu + chạy thử trên máy thật)
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/src-sync-pc0575.md`
- Đầu vào bắt buộc đọc trước: mục 2.3 + 2.4 của `docs/phieu-viec/ket-qua/lsu-quality-pc0575.md` và báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-cty.md` (chuỗi bằng chứng rào vân tay).

## Bối cảnh

Index trên PC0575 (889 tài liệu / 149.800 chunk, khôi phục ở vé RESTORE-INDEX-SPLIT)
tham chiếu file nguồn theo đường dẫn của **máy đã dựng index** (`gpu-dc://…`,
`materialized_sources/…`) — trên máy công ty hiện có **0/889 file nguồn**. Hệ quả đã
đo được 2 lần (vé DIGEST-CTY-RESUME + vé LSU-QUALITY-PC0575):
- Cấu hình thật của app (`strict_semantic=True`) chặn truy vấn toàn kho:
  `semantic_index_coverage_incomplete`.
- Bộ lọc vân tay nguồn xóa ứng viên hàng loạt (`filtered_as_stale_count=120958`).
- Mọi lượt đo RAG đến nay phải **hạ 2 cổng vân tay + tắt strict_semantic** — tức RAG
  trên máy công ty CHƯA từng chạy đúng thiết kế.

Vé này xử lý gốc: làm cho file nguồn có mặt trên PC0575 đúng chỗ index mong đợi,
để RAG chạy `strict_semantic=True` không cần hạ cổng nào.

## Việc cần làm

### Pha 0 — Điều tra (làm ngay, không cần chờ cổng mạng)
1. Đọc index (chỉ-đọc) + code đường retrieval: index mong đợi file nguồn ở đâu, dạng nào
   (file gốc hay bản materialized `.txt`), tổng dung lượng cần bao nhiêu.
2. Kiểm tra ổ đĩa PC0575: còn trống bao nhiêu, đủ không (ghi số thật).
3. Xác định nguồn kéo: thư mục Drive `AIOS_Data` (MOM / LSU / Dieu-tra-loi) — đối chiếu
   danh sách 889 tài liệu trong index với file trên Drive, liệt kê thiếu/thừa.
4. Ghi kết quả Pha 0 vào báo cáo nháp + mốc mailbox, rồi **DỪNG Ở CỔNG MẠNG** (Pha 1).

### Pha 1 — CHUYỂN MẠNG (thợ tự làm theo QUY-UOC, KHÔNG chờ xác nhận — cập nhật 2026-10-07)
- Chạy: `powershell -ExecutionPolicy Bypass -File "D:\Sandbox\agent-mailbox\Chuyen-Mang.ps1" -Mang ngoai`
- Kiểm output `DRIVE=OK` rồi mới tải. `DRIVE=FAIL`: ghi mốc mailbox, chờ nhịp sau thử lại — không tải bừa.
- Tải xong: chuyển về `-Mang congty` (vé sau cần LAN/C-Agent).

### Pha 2 — Đồng bộ + kiểm chứng (sau khi cổng mở)
1. Tải file nguồn về, đặt đúng đường dẫn index mong đợi (hoặc cơ chế ánh xạ tương đương —
   ghi rõ chọn cách nào và vì sao).
2. Kiểm chứng: chạy probe RAG vài câu thật (lấy từ bộ 50 câu LSU) với cấu hình ĐÚNG THIẾT KẾ
   (`strict_semantic=True`, KHÔNG hạ cổng vân tay) — phải trả lời được, không còn lỗi
   `semantic_index_coverage_incomplete`.
3. Đo md5 index trước/sau: phải KHÔNG đổi (vé này không ghi index).
4. Báo cáo `src-sync-pc0575.md`: dung lượng đã kéo, số file khớp 889, kết quả probe strict,
   cách khôi phục nếu cần.

## Rào cứng

- KHÔNG ghi/sửa index. KHÔNG đụng `wire_qa_staging.py` (OMP đang vá ở vé MATCHER-FIX-PC0575).
- KHÔNG restart app khi OMP đang chạy đo giữa chừng — cần restart thì ghi mốc mailbox trước.
- Nếu Pha 0 chứng minh không khả thi (thiếu đĩa / nguồn Drive không đủ 889): DỪNG, báo cáo
  bằng chứng + đề xuất phương án khác (vd chế độ index-only chính thức) — không cố làm bừa.
- Không merge `main`. Không secret trong báo cáo/log.

## Quy ước heartbeat + checkpoint

- Mỗi bước ghi 1 dòng `ghi_chu` mốc bước vào mailbox, tối thiểu 15 phút/lần.
- Mỗi pha xong ghi kết quả vào báo cáo nháp ngay (checkpoint/resume).

## Tiêu chí nghiệm thu

- ĐẠT = file nguồn có mặt đủ (khớp danh sách index) + probe RAG chạy `strict_semantic=True`
  không hạ cổng vẫn trả lời được + md5 index không đổi.
- Nếu chuyển mạng `ngoai` mà `DRIVE=FAIL` kéo dài: ghi trạng thái "kẹt cổng mạng" kèm output làm bằng chứng — không coi là xong vé.
