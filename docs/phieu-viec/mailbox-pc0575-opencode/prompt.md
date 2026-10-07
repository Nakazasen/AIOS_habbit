# VÉ: SRC-PROBE-PC0575 (probe RAG đầu-cuối cho 29 tệp nguồn đã khôi phục)

- Mã vé: `SRC-PROBE-PC0575`
- Role gợi ý: DEFAULT
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/src-probe-pc0575.md`
- Đầu vào bắt buộc đọc trước: `docs/phieu-viec/ket-qua/src-sync-pc0575.md` (đặc biệt mục 7: 29 tệp đã khôi phục; mục 8: vân tay logic mốc `87a3626a…`).

## Bối cảnh

Vé `SRC-SYNC-PC0575` phần máy công ty đã verdict ĐẠT (07/10): 29 tệp nguồn được khôi phục từ nội dung mảnh trong chỉ mục và qua probe mô phỏng cổng stale. Nhưng báo cáo mục 7 ghi rõ còn thiếu bước cuối: **chưa chạy probe RAG đầy đủ với `strict_semantic=True`** trên các tệp này. Vé này khép điểm đó — chứng minh 29 tệp thật sự chảy qua được toàn bộ đường truy hồi thật, không chỉ qua mô phỏng.

## Việc phải làm

1. Với **từng tệp trong 29 tệp đã khôi phục**: chạy một truy vấn thật qua pipeline RAG đầy đủ (bật `strict_semantic`), kiểm chứng tài liệu:
   - qua cả 3 cổng vân tay (không rơi `__source_unavailable__`, không bị đánh dấu stale, qua cổng hybrid-safe);
   - xuất hiện được trong kết quả truy hồi của pipeline.
2. Đối chứng bắt buộc:
   - **Âm:** 5 tài liệu thuộc nhóm 511 chưa có tệp — kỳ vọng bị chặn ở cổng unavailable (nếu tài liệu nào "qua" thì đó là phát hiện bất thường, ghi rõ).
   - **Dương:** 5 tài liệu vốn có tệp sẵn từ đầu — kỳ vọng qua cả 3 cổng.
3. Báo cáo: bảng kết quả từng tài liệu (mã, cổng nào qua/rớt, ghi chú) + kết luận tổng. Nếu có tệp khôi phục nào rớt ở pipeline thật: dừng ở tài liệu đó, ghi bằng chứng đầy đủ (thông điệp cổng, mã lỗi) và báo điều phối trong mailbox — không tự sửa tệp/index trong vé này.

## Rào cứng

- Chỉ-đọc chỉ mục; không ghi/sửa tệp nguồn hay index; không đụng `src/rag_v2*` (WIP của agy) — chỉ chạy pipeline như người dùng cuối.
- Cần mạng LAN cho bước nào thì tự chuyển theo QUY-UOC và chuyển về sau khi xong.
- Không merge `main`. Không xóa dữ liệu đã tải ở `local_runs/src_sync`.
