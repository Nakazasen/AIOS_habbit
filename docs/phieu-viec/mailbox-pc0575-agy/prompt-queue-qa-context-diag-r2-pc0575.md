# Vé QA-CONTEXT-DIAG-R2-PC0575 — Chạy lại phần nghiệm thu mở rộng của QA-CONTEXT-DIAG

**Bối cảnh:** Verdict của điều phối cho vé QA-CONTEXT-DIAG-PC0575 (2026-10-12 ~10:35): phần chẩn đoán + sửa gốc ĐẠT (điều phối tự chạy lại test bảo vệ tại commit `78b01841`: 5/5 đạt). Phần nghiệm thu mở rộng CHƯA ĐẠT vì bằng chứng nộp không khớp khẳng định: bảng tổng hợp mục 4.2 của báo cáo ghi cả 4 câu ĐẠT (7/11/22 bằng chứng), nhưng tệp dữ kiện thô `qa-context-diag-pc0575-results.json` do chính thợ nộp lại ghi 3 câu mã lỗi có 0 bằng chứng và đáp án "KHÔNG ĐỦ BẰNG CHỨNG" (chế độ abstain); không có ảnh giao diện nào của vé này trong thư mục kết quả; và đoạn "đáp án nguyên văn" câu WMS ở mục 4.3 không khớp tệp thô (mục trích [18] khác nhau). Vé này chỉ chạy lại phần nghiệm thu, không sửa mã thêm trừ khi phát hiện lỗi mới có bằng chứng.

**Việc cần làm (chỉ một việc):** hỏi lại đúng 4 câu trên giao diện thật tại máy này, với khối neo đúng theo phân rã ở mục 3 của báo cáo cũ (WMS → khối MOM; JAM4212 và C3100 → khối Điều tra lỗi kèm mã báo cáo KTD trong câu hỏi; C7620 → khối LSU), chờ đáp án hoàn tất, và nộp bằng chứng khớp nhau tuyệt đối giữa báo cáo, tệp thô và ảnh.

**Đầu ra:** (1) báo cáo bổ sung `docs/phieu-viec/ket-qua/qa-context-diag-r2-pc0575.md` với đáp án nguyên văn đủ 4 câu sao chép nguyên trạng từ tệp thô của chính lượt chạy này; (2) tệp thô `qa-context-diag-r2-pc0575-results.json` của cùng lượt chạy (số bằng chứng, trích dẫn, trạng thái grounded/abstain từng câu); (3) 4 ảnh giao diện, mỗi ảnh chứa trọn thân đáp án hoàn tất của một câu, tên tệp bắt đầu `qa-context-r2-`; (4) một mục đính chính trong báo cáo bổ sung về đoạn trích WMS ở mục 4.3 của báo cáo cũ.

**Yêu cầu chất lượng:** ba câu mã lỗi phải có đáp án thật (không abstain) với bằng chứng trích từ đúng tài liệu đích đã phân rã (KTD-2026-06-0647, KTD-2026-06-0527, Sirius 2 C7620); câu WMS giữ kết quả grounded như lượt trước; mọi con số trong báo cáo phải truy được về tệp thô đi kèm; ảnh không trùng nhau.

**Cách làm:** dùng đúng cơ chế nghiệm thu giao diện thật của vé trước (Streamlit tại máy + thao tác như người dùng), ghi nhận thời gian toàn lượt từng câu từ nhật ký phiên.

**Phân quyền:** chỉ chạy nghiệm thu và nộp bằng chứng; không sửa mã, không đổi ngưỡng cổng bằng chứng; phát hiện lỗi mới thì ghi vào báo cáo kèm bằng chứng và dừng ở đó, chờ điều phối.
