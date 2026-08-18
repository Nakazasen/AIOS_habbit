# Dự Thảo Kế Hoạch Mở Cổng P1 (P1 Opening Plan Draft)

Đây chỉ là bản dự thảo kế hoạch. Nó không tự ý mở cổng P1.0.

## Trạng Thái Hiện Tại (Current Status)

- P1.0: ĐÃ ĐÓNG (CLOSED)
- Tương đương NotebookLM (NotebookLM parity): KHÔNG TUYÊN BỐ (NOT_CLAIMED)
- Nghiệm thu thực tế của chủ sở hữu: BỊ CHẶN, CẦN NGHIỆM THU (BLOCKED_NEEDS_OWNER_ACCEPTANCE)
- Cổng đẩy lên Git (Push gate): ĐANG CHỜ CỔNG ĐẨY (PENDING_PUSH_GATE)

## Yêu Cầu Bắt Buộc Trước Khi Có Thể Mở P1.0

1. Chủ sở hữu là con người hoàn thành [Sổ tay nghiệm thu của chủ sở hữu cho P1](P1_OWNER_ACCEPTANCE_RUNBOOK.md).
2. Chủ sở hữu báo cáo ĐẠT (PASS) với gánh nặng thao tác thủ công ở mức chấp nhận được.
3. Toàn bộ bài kiểm thử pytest chạy đạt (PASS).
4. Kiểm toán CLI audit chạy đạt (PASS).
5. Quét secret / runtime / artifact tự sinh chạy đạt (PASS).
6. Các quy tắc bảo mật được kiểm tra lại cho cả hai tuyến `local_only` và `cloud_safe`.
7. Đo chuẩn RAG benchmark đạt theo các tiêu chí đã thống nhất.
8. Tài liệu không đưa ra các tuyên bố tương đương hay thay thế NotebookLM.

## Các Cải Tiến Tùy Chọn Trước P1.0

- Sử dụng bộ soạn thảo câu trả lời tất định cục bộ cho các bản thảo có trích dẫn cục bộ.
- Chỉ sử dụng bộ xếp hạng lại (reranker) tất định cục bộ như một cải tiến chất lượng tìm kiếm / benchmark dạng opt-in.
- Chỉ bổ sung ảnh chụp màn hình hướng tới chủ sở hữu bằng dữ liệu giả lập (synthetic data).

## Các Phi Mục Tiêu Rõ Ràng Cho Việc Mở P1

- Không đưa vào Vector DB trừ khi bằng chứng đo chuẩn benchmark chứng minh điều đó là bắt buộc.
- Không đưa vào Graph DB trừ khi các truy vấn đồ thị quan hệ xuyên vụ việc trở nên bắt buộc đối với P1.
- Không tự động hóa gọi provider / cloud đối với nội dung công ty hoặc nhạy cảm.
- Không tuyên bố tương đương năng lực với NotebookLM.

## Quyết Định Mở Cổng (Opening Decision)

P1.0 chỉ có thể được mở sau khi lượt chạy nghiệm thu của chủ sở hữu hoàn tất và tất cả các cổng kiểm chứng đều đạt (PASS).

