# VÉ: INDEX-RESTORE-HOME (khôi phục chỉ mục production máy nhà từ bản gốc đã đóng dấu)

- Mã vé: `INDEX-RESTORE-HOME`
- Role gợi ý: DEFAULT (thao tác theo quy trình chặt, không suy diễn)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/index-restore-home.md`
- Căn cứ: user đã DUYỆT khôi phục tại chat 2026-10-08 ~16:07 +07 (lựa chọn "Khôi phục ngay chỉ mục máy nhà từ bản gốc đã đóng dấu (có sao lưu bản hiện tại trước)"). Nền tảng: báo cáo `index-hash-drift-trace-home.md` (bản gốc khôi phục tại `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`, SHA-256 `45EB0E07…B7C0` khớp 100% chuẩn đóng dấu) + vé `INDEX-READONLY-GUARD-HOME` đã ĐẠT (đường giao diện đã bị khoá ghi).

## Quy trình bắt buộc (đúng thứ tự, dừng ngay và báo cáo nếu bất kỳ cổng nào không khớp)

1. **Dừng tiến trình:** dừng toàn bộ Streamlit và BGE persistent worker trên máy nhà; xác nhận không còn tiến trình nào giữ tệp `library.sqlite` (kể cả các tệp phụ `-wal`/`-shm` nếu có — ghi rõ trạng thái của chúng trong báo cáo).
2. **Sao lưu trạng thái hiện tại (đường quay lui):** chép tệp production hiện tại (băm `B0B873D0…3EE6`) sang thư mục sao lưu mới có dấu thời gian (vd `D:\Sandbox\AIOS_index_backup\20261008-pre-restore\`), kèm kiểm chứng: băm của bản sao lưu phải khớp `B0B873D0…3EE6` và `PRAGMA integrity_check` (mở chỉ đọc) = ok. Không qua được cổng này thì DỪNG, không chép đè.
3. **Kiểm chứng nguồn khôi phục:** tính lại SHA-256 + dung lượng của tệp nguồn sao lưu gốc; phải khớp tuyệt đối `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` và 2.942.201.856 byte. Lệch thì DỪNG.
4. **Dọn hệ quả phụ của tài liệu trùng:** xóa tệp `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources\wsc-b9e2ffa072623484b1fa4198.txt`; xóa bản ghi của `document_id = wsc-b9e2ffa072623484b1fa4198` trong ledger chuẩn bị nguồn (ghi rõ DB ledger nằm ở đâu và đã xóa bao nhiêu dòng).
5. **Chép khôi phục:** chép tệp nguồn gốc đè lên tệp production đích (sau khi đã xử lý tệp `-wal`/`-shm` của đích nếu còn tồn tại — ghi rõ cách xử lý).
6. **Kiểm chứng sau khôi phục (mở `mode=ro&immutable=1`):** SHA-256 của tệp đích khớp tuyệt đối `45EB…B7C0`; đếm: 889 tài liệu / 149.800 mảnh / 121.331 mảnh truy hồi được; `integrity_check` = ok.
7. **Nghiệm thu guard bằng phiên app thật (bằng chứng cuối):** mở app, KHÔNG bật thêm nguồn mới nào, hỏi 1 câu đã biết đáp án trên nguồn có sẵn trong kho; sau phiên, tính lại SHA-256 của tệp production — phải VẪN khớp `45EB…B7C0`. Nếu băm đổi: DỪNG NGAY, báo cáo chi tiết, không chạy thêm phiên nào. (Đây là bằng chứng đầu-cuối rằng khoá chỉ đọc mới đã hiệu lực trên đường thật.)

## Rào cứng

- Không bước nào được bỏ qua sao lưu ở Bước 2; sao lưu xong mới chép đè.
- Ngoài các thao tác trong quy trình này: không ghi thêm bất cứ thứ gì vào chỉ mục; không sửa code ở vé này.
- Báo cáo phải ghi: băm + dung lượng ở từng cổng (trước sao lưu / bản sao lưu / nguồn / sau khôi phục / sau phiên app), số đếm 889/149.800/121.331, tình trạng tệp `-wal`/`-shm`, số dòng ledger đã xóa.
- Không merge `main`. Mốc tiến độ tối thiểu 15 phút/lần.
