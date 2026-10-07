# VÉ: RETRIEVAL-ENTITY-PC0575 (ràng buộc thực thể + chống lấn át trong retrieval — fix nhóm A)

- Mã vé: `RETRIEVAL-ENTITY-PC0575`
- Máy: CÔNG TY KDTVN-PC0575 (thợ agy), CPU-only.
- Role gợi ý: DEFAULT (code + test + kiểm chứng mức retrieval).
- Nguồn: `docs/phieu-viec/ket-qua/rag-fail-analysis-pc0575.md` §4.3 + §5 Ưu tiên 2 (tác động kỳ vọng +0,280 GPA lane RAG).

## Bối cảnh

Nhóm A — 7 câu retrieval trượt (mất 14,0 điểm): tài liệu ĐÃ có trong index (`Sirius 2`, `OKNGUNIT`, `3V2ND19040`, `Y_BeamH_Camera 140`…) nhưng mảnh đúng không vào được top-k vì tệp khổng lồ `Loi KDTPS.xlsx` lấn át kết quả. Danh sách 7 câu: xem §4.3 của báo cáo phân tích.

## Việc phải làm

0. **Đóng dấu thước đo vào repo (việc nhỏ, làm trước):** commit bộ đề 50 câu + bộ từ khóa đã chuẩn hoá (đúng trạng thái đã dùng khi chấm lại ở vé RUBRIC-NORMALIZE) vào repo — đường dẫn fixtures/eval rõ ràng, kèm ghi chú nguồn gốc. Từ nay thước đo phải tái lập được từ repo.
1. **Entity Matching Boost:** khi câu hỏi chứa mã lỗi chuyên biệt (ví dụ `C7620`) hoặc số hiệu đồ gá/tên chuyên đề (`1035`, `MOUNT LD BLOCK`, `Sirius 2`…), tăng trọng số cho tài liệu có thực thể đó trong tiêu đề/nội dung đầu. Boost phải có trần, không áp đảo hoàn toàn điểm liên quan gốc.
2. **Diversity Capping:** tối đa **3 mảnh từ một tệp nguồn duy nhất** trong top-k ngữ cảnh (ca điển hình: `Loi KDTPS.xlsx`). Cap áp ở tầng chọn ngữ cảnh, ghi log khi cap kích hoạt.
3. **Test:** tái lập ca lấn át (tệp lớn chiếm gần hết top-k → sau vá ≤3); ca boost thực thể (câu có mã lỗi → tài liệu chuyên đề vào top-k); ca không đổi hành vi khi câu hỏi không có thực thể.

## Nghiệm thu (mức retrieval — KHÔNG chạy lại lane ở vé này)

- Trên đúng 7 câu nhóm A: mảnh/tài liệu đúng vào top-k ở **7/7 câu** (trước vá: trượt cả 7 theo báo cáo).
- Hồi quy test retrieval liên quan xanh; không đổi hành vi lane C-Agent (matcher không thuộc vé này).
- Đo lại toàn lane để sau, khi các fix đã gom đủ (matcher + thước đo + retrieval + bổ sung nguồn) — vé này chỉ cần bằng chứng mức retrieval.

## Rào cứng

- Không merge `main`. Không ghi index. Python 3.11.
- Không đụng `wire_qa_staging.py` (vé MATCHER-FIX của OMP) và không đụng `rag_v2/synthesis.py` (việc máy nhà). Nếu cơ chế boost/cap buộc phải chạm file chung, DỪNG và ghi rõ vào mailbox chờ điều phối.
- Heartbeat tối thiểu 15 phút nếu việc kéo dài.

## Báo cáo

`docs/phieu-viec/ket-qua/retrieval-entity-pc0575.md` — đường dẫn bộ đề đã commit, cơ chế boost/cap, bảng top-k trước/sau cho 7 câu nhóm A, kết quả test.
